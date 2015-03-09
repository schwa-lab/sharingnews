#!/usr/bin/env python

from __future__ import print_function, absolute_import, division

import traceback

from django.db import transaction

from likeable.idqueue import main, json_log
from likeable.models import DownloadedArticle, Article


DEST_FIELDS = DownloadedArticle.EXTRACTED_FIELDS


@transaction.atomic
def extract(args, article_id):
    if extract.count % 1000 == 0:
        json_log(count=extract.count)
    extract.count += 1

    try:
        downloaded = DownloadedArticle.objects.select_related('article__url_signature') \
                                      .defer(*DEST_FIELDS) \
                                      .get(article_id=article_id)
    except DownloadedArticle.DoesNotExist:
        json_log(article_id=article_id, status='unknown ID or not downloaded')
        return

    signature = downloaded.article.url_signature
    if signature is None:
        json_log(article_id=article_id, status='no signature assigned',
                 exception='no signature')
        return

    if not downloaded.needs_extraction:
        json_log(article_id=article_id, status='already marked clean')
        return

    try:
        parsed = downloaded.parsed_html
    except Exception as exc:
        json_log(article_id=article_id, status='exception in parsing',
                 exception=repr(exc), traceback=traceback.format_exc())
        return
    if parsed is None:
        json_log(article_id=article_id, status='parsed_html is None')
        if not downloaded.article.title:
            downloaded.article.fetch_status = Article.CUSTOM_FETCH_STATUS['effectively empty content']
            downloaded.article.save()
            downloaded.delete()
        return
    for field in DEST_FIELDS:
        extractor = getattr(signature, 'extract_' + field)
        setattr(downloaded, field, extractor(parsed, as_unicode='join') or None)

    downloaded.scrape_when = signature.modified_when
    downloaded.save()

extract.count = 0


if __name__ == '__main__':
    main('extract', extract)
