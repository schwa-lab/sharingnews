#!/usr/bin/env python

from __future__ import print_function, absolute_import, division

from lxml import etree
from django.db import transaction

from likeable.idqueue import main, json_log
from likeable.models import DownloadedArticle


DEST_FIELDS = DownloadedArticle.EXTRACTED_FIELDS


def join_extractions(extr):
    extr = [etree.tounicode(el) if hasattr(el, 'tag') else unicode(el)
            for el in extr]
    extr = [s.replace('\r', '').replace('\n', ' ') for s in extr]
    return '\n'.join(extr)


@transaction.atomic
def extract(args, article_id):
    try:
        downloaded = DownloadedArticle.objects.get(id=article_id)\
                                      .select_related('article__signature')\
                                      .defer(DEST_FIELDS)
    except DownloadedArticle.DoesNotExist:
        json_log(article_id=article_id, status='unknown ID or not downloaded')
        return

    signature = downloaded.article.signature

    if downloaded.scrape_when is not None and \
       downloaded.scrape_when > signature.modified_when:
        json_log(article_id=article_id, status='already marked clean')
        return

    xpatheval = etree.XPathEvaluator(downloaded.parsed_html)
    for field in DEST_FIELDS:
        xpath = getattr(signature, field + '_xpath')
        if xpath is None:
            continue
        extr = xpatheval(xpath)
        setattr(downloaded, field, join_extractions(extr) or None)

    downloaded.scrape_when = signature.modified_when
    downloaded.save()


if __name__ == '__main__':
    main('extract', extract)
