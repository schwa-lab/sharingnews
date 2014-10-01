#!/usr/bin/env python
from __future__ import print_function
import os
import sys
import re
import traceback

from bs4 import UnicodeDammit
import django
from django.core.exceptions import ObjectDoesNotExist

from likeable.models import Article, DownloadedArticle, ShareWarsUrl
from likeable.cleaning import extract_canonical, compress_html

django.setup()

# Uh oh. What do we do with URLs that share a canonical but don't have same CSS? Ideally we should download the canonical, but that's not something we've done so far.


def process_path(stat_path):
    print(stat_path)
    # could map by ID, instead using canonical for certainty
    with open(stat_path) as stat_file:
        lines = [l.rstrip('\n\r').split('\t') for l in stat_file]
    try:
        # start_url = lines[0][1]
        status, end_url, mime = lines[-1]
    except IndexError:
        print('Failed to extract stat data for', stat_path, file=sys.stderr)
        return

    # TODO: exclude non-HTML MIME

    try:
        with open(os.path.splitext(stat_path)[0] + '.html') as data_file:
            content = data_file.read()  # TODO: suggest charset!
    except IOError:
        content = None
        canonical = end_url
    else:
        ud = UnicodeDammit(content, is_html=True)
        if ud.unicode_markup is None:
            raise UnicodeDecodeError('UnicodeDamit failed for ' + stat_path)
        content = ud.unicode_markup
        content = re.sub(u'<!--.*?-->', '', content, re.DOTALL).strip()
        canonical = extract_canonical(content, end_url) or end_url

    swid = int(os.path.basename(stat_path).rsplit('.', 1)[0])
    sw_article = ShareWarsUrl.objects.select_related('spidered__article').get(id=swid).spidered.article
    sw_url = getattr(sw_article, 'url', None)
    if sw_url != canonical:
        print('For', stat_path, 'got', sw_url, 'via FB but', canonical,
              'via fetch', file=sys.stderr)

    try:
        article = Article.objects.get(url=canonical)
    except Article.DoesNotExist:
        print('WARNING Failed to lookup', canonical, 'for', stat_path, file=sys.stderr)
        return

    # fetch_when?
    if not status.startswith('2'):
        if status.startswith('<'):
            # Client-side exception occurred, often timeout
            status = 500
        status = int(status)
        if article.fetch_status is not None and article.fetch_status != status:
            print('Found fetch_status', article.fetch_status, 'so not saving', status, 'for', canonical, file=sys.stderr)
            return
        article.fetch_status = status
        article.save()
        return

    if article.fetch_status == 200:
        try:
            assert article.downloaded is not None
        except ObjectDoesNotExist:
            pass
        else:
            print('Skipped duplicate', stat_path, 'fbid=', article.id, file=sys.stderr)
            return
    if article.fetch_status is not None:
        print('Found fetch_status', article.fetch_status, 'so overwriting with 200 from', stat_path, 'for', canonical, file=sys.stderr)
    article.fetch_status = int(status)
    try:
        if article.downloaded is not None:
            raise RuntimeError('Unexpected not-null downloaded for ' + canonical)
    except ObjectDoesNotExist:
        pass
    if not content:
        raise RuntimeError('Unexpected non-content for ' + stat_path)
    article.downloaded = DownloadedArticle(article=article, in_dev_sample=True,
                                           html=compress_html(content))
    article.downloaded.save()
    article.save()
    print('SUCCESS:', stat_path, '=', canonical, 'fbid=', article.id, file=sys.stderr)


for stat_path in sys.argv[1:]:
    try:
        process_path(stat_path)
    except Exception as e:
        print('ERROR processing', stat_path, file=sys.stderr)
        traceback.print_exc(e)
