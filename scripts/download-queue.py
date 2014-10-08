#!/usr/bin/env python

from __future__ import print_function, absolute_import, division
import time
import random
from collections import defaultdict
import traceback

from django.db import transaction
from bs4 import UnicodeDammit

from likeable.idqueue import main, utcnow, json_log
from likeable.models import Article, DownloadedArticle
from likeable.scraping import (fetch_with_refresh, HTTP_ENCODINGS,
                               FetchException, get_mime)
from likeable.cleaning import compress_html, extract_canonical


domain_encodings = defaultdict(lambda: list(HTTP_ENCODINGS))


def _save_article(article, response, timestamp):
    status = response.status_code
    article.fetch_status = status
    # TODO: assert downloaded does not exist, or perhaps replace it?
    if status != 200:
        article.save()
        return

    # TODO: mime check?

    content = response.content  # get content, interpret as unicode
    override_encodings = ([response.encoding]
                          if response.encoding is not None else [])
    ud = UnicodeDammit(content, override_encodings=override_encodings,
                       is_html=True)
    if ud.unicode_markup is None:
        raise UnicodeDecodeError('UnicodeDammit failed for '
                                 '{}'.format(article.id))
    content = ud.unicode_markup

    canonical = extract_canonical(content)
    if canonical == article.url:
        canonical = None

    downloaded = DownloadedArticle(article=article,
                                   html=compress_html(content),
                                   fetch_when=timestamp,
                                   canonical_url=canonical)
    downloaded.save()
    article.save()


def _save_log(article, prior_status, hops, exc):
    status = 'exception' if exc is not None else hops[-1].status_code
    reqs = [{'status': hop.status_code,
             'url': hop.url,
             'mime': get_mime(hop),
             }
            for hop in hops]
    if hasattr(exc, 'underlying'):
        tb = ''.join(traceback.format_exception(*exc.exc_info))
        reqs.append({'url': exc.url,
                     'exception': repr(exc.underlying),
                     'traceback': tb,
                     })
    data = {
        'article_id': article.id,
        'status': status,
        'requests': reqs,
    }
    if prior_status is not None:
        data['prior_status'] = prior_status
    json_log(**data)


@transaction.atomic
def download_and_save(args, article_id):
    try:
        article = Article.objects.get(id=article_id)
    except Article.DoesNotExist:
        json_log(article_id=article_id, status='unknown ID')
        return

    url = article.url
    prior_status = article.fetch_status

    if prior_status == 200:
        json_log(article_id=article_id, status='skipped')
        return

    time.sleep(random.random())
    domain = url.split('/', 3)[2]
    timestamp = utcnow()
    try:
        hops = fetch_with_refresh(url,
                                  accept_encodings=domain_encodings[domain])
    except FetchException as exc:
        hops = exc.hops
    else:
        exc = None

    if exc is None:
        if not hops[-1].content and hops[-1].status_code == 200:
            json_log(article_id=article_id, status='empty content')
            return

        _save_article(article, hops[-1], timestamp)
    # TODO: perhaps save pseudo-status on exception

    _save_log(article, prior_status, hops, exc)


if __name__ == '__main__':
    main('fetch', download_and_save)
