#!/usr/bin/env python

from __future__ import print_function, absolute_import, division

import traceback

from lxml import etree
from django.db import transaction

from likeable.idqueue import main, json_log
from likeable.models import DownloadedArticle
from likeable.scraping import extractions_as_unicode


DEST_FIELDS = DownloadedArticle.EXTRACTED_FIELDS


@transaction.atomic
def extract(args, article_id):
    if extract.count % 1000 == 0:
        json_log(count=extract.count)
    extract.count += 1

    try:
        downloaded = DownloadedArticle.objects.select_related('article__signature') \
                                      .defer(*DEST_FIELDS) \
                                      .get(article_id=article_id)
    except DownloadedArticle.DoesNotExist:
        json_log(article_id=article_id, status='unknown ID or not downloaded')
        return

    signature = downloaded.article.url_signature

    if downloaded.scrape_when is not None and \
       downloaded.scrape_when > signature.modified_when:
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
        return
    xpatheval = etree.XPathEvaluator(parsed)
    for field in DEST_FIELDS:
        xpath = getattr(signature, field + '_xpath')
        if xpath is None:
            setattr(downloaded, field, None)
            continue
        extr = xpatheval(xpath)
        setattr(downloaded, field, extractions_as_unicode(extr, join=True) or None)

    downloaded.scrape_when = signature.modified_when
    downloaded.save()

extract.count = 0


if __name__ == '__main__':
    main('extract', extract)
