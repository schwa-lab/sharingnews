#!/usr/bin/env python
"""
Stores the output of scripts/join-weekly-delta.py in the database under Facebook ID
"""
import json
import itertools
import datetime
import re

from django.utils.lru_cache import lru_cache
from dateutil.tz import tzutc
from django.db import transaction

from likeable.idqueue import main, json_log
from likeable.countapis import FBBatchFetcher, FB_URL_FIELDS
from likeable.cleaning import url_signature, strip_subdomains
from likeable.models import Article, UrlSignature, ShareWarsUrl, SpideredUrl


UTC = tzutc()


@lru_cache(maxsize=1)
def load_fb_prefetched(glob_expr='data/fb-fetch2/*.multijson'):
    import glob
    out = {}
    for path in glob.glob(glob_expr):
        for l in open(path):
            out.update(json.loads(l))
    return out


@lru_cache(maxsize=50)
def _get_base_domain_sig(domain):
    obj, created = UrlSignature.objects.only('signature', 'id', 'base_domain')\
                                       .get_or_create(defaults={'base_domain': domain},
                                                      signature=domain)
    if created:
        obj.save()
    return obj


@lru_cache(maxsize=50)
def _get_or_create_sig(sig):
    obj, created = UrlSignature.objects.only('signature', 'id', 'base_domain')\
                                       .get_or_create(signature='/'.join(sig))
    if created:
        obj.base_domain = strip_subdomains(sig[0])
        backoff = obj.get_backoff(_get_base_domain_sig(obj.base_domain))
        for k, v in backoff.items():
            obj.set_selector(k, v)
        obj.save()
    return obj


def _parse_iso8601(s):  # parses as UTC
    return datetime.datetime(*map(int, re.split('[^\d]', s)[:-1]), tzinfo=UTC)


def process(args, body):
    header, _, body = body.partition('\n')
    fields = header.split('|')
    url_field = fields.index('article_Url')
    swid_field = fields.index('article_Id')
    body = [l.split('|') for l in body.split('\n') if l]
    to_skip = list(ShareWarsUrl.objects.filter(id__in=[int(l[swid_field]) for l in body]).values_list('id', flat=True))
    n_skipped = len(to_skip)
    if n_skipped:
        body = [l for l in body if int(l[swid_field]) not in to_skip]
    # Perhaps begin by get-or-create sharewarsurl
    urls = [l[url_field] for l in body]
    # FIXME: time.sleep use in batch fetcher may be problematic to pika
    # XXX: might be better to rely on rabbitmq for retry

    #fb_prefetched = load_fb_prefetched()  # constant and cached
    fb_prefetched = {}

    fb_result = FBBatchFetcher(FB_URL_FIELDS).fetch_auto([url for url in urls if url not in fb_prefetched])
    if not fb_result.startswith('{'):
        raise ValueError('Got result from FBBatchFetcher not beginning with {')
    # Now create Article if necessary
    # Then wait for download cron (TBC) to run!
    fb_result = json.loads(fb_result)
    prefetched_content = {url: fb_prefetched[url] for url in urls if url in fb_prefetched}
    fb_result.update(prefetched_content)

    n_created = 0
    for record in body:
        record = dict(zip(fields, record))
        _, created = create_article(record, fb_result[record['article_Url']])
        n_created += created
    json_log(n_processed=len(body), n_created=n_created, sharewars_id_example=body[0][0] if body else None, prefetched=len(prefetched_content),
             skipped=n_skipped)


def create_article(record, fb_record):
    if fb_record is None:
        json_log(error='Got null fb_record from Facebook', sharewars_id=record['article_Id'], initial_url=record['article_Url'])
    if 'og_object' not in fb_record:
        if 'share' in fb_record:
            json_log(error='Got no og_object from Facebook, but got share!', sharewars_id=record['article_Id'], initial_url=record['article_Url'])
        else:
            json_log(error='Got no og_object from Facebook', sharewars_id=record['article_Id'], initial_url=record['article_Url'])
        return None, False
    initial_url = record['article_Url']
    final_url = fb_record['og_object']['url']
    with transaction.atomic():
        initial_sig = _get_or_create_sig(url_signature(initial_url.encode('utf8')))
    if initial_url == final_url:
        final_sig = initial_sig
    else:
        with transaction.atomic():
            final_sig = _get_or_create_sig(url_signature(final_url.encode('utf8')))

    with transaction.atomic():
        article, created = Article.objects.get_or_create(id=fb_record['og_object']['id'], defaults={'url': fb_record['og_object']['url']})
        spider_when = _parse_iso8601(record['article_Date'])
        site_id = int(record['site_Id'])

        spidered_url, _ = SpideredUrl.objects.get_or_create(url=initial_url,
                                                            defaults={'url_signature': initial_sig,
                                                                      'article': article})
        sharewars_url, _ = ShareWarsUrl.objects.get_or_create(id=record['article_Id'],
                                                              defaults={'when': spider_when,
                                                                        'site_id': int(site_id),
                                                                        'spidered': spidered_url})
        if not created and spider_when >= article.spider_when and article.url:
            return article, False

        article.url = fb_record['og_object']['url']
        article.url_signature = final_sig
        article.title = fb_record['og_object'].get('title')
        article.fb_has_title = article.title is not None
        #article.description = fb_record['og_object'].get('description')
        for offset, values in json.loads(record['statistic_Json']).items():
            fb, _, tw = values.partition(',')
            setattr(article, 'fb_count_' + offset, fb)
            setattr(article, 'tw_count_' + offset, tw)
        article.spider_when = spider_when
        try:
            article.fb_created = fb_record['og_object']['created_time']
        except KeyError:
            json_log(error='Got no FB created time', fb_record=fb_record, sharewars_id=record['article_Id'], initial_url=record['article_Url'])
        article.sharewars_site_id = int(site_id)
        article.save()
        assert Article.objects.get(id=article.id).sharewars_site

    return article, True


def enqueue_generator(args, f):
    header = f.next()
    chunk = '\n'.join(itertools.islice(f, 0, args.batch_size))
    while chunk:
        yield header + '\n' + chunk
        chunk = '\n'.join(itertools.islice(f, 0, args.batch_size))


def argparse_cb(ap):
    # should really be in subparse, but how?
    ap.add_argument('--batch-size', default=40, type=int, help='Batch size to enqueue')


if __name__ == '__main__':
    main('ingest', process, enqueue_generator=enqueue_generator, argparse_cb=argparse_cb)
