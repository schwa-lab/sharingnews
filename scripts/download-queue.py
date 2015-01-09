#!/usr/bin/env python

from __future__ import print_function, absolute_import, division
import time
import random
from collections import defaultdict
import traceback

from django.db import transaction

from likeable.idqueue import main, json_log
from likeable.models import Article
from likeable.scraping import (HTTP_ENCODINGS, FetchException, get_mime)
from likeable.structure import sketch_doc


domain_encodings = defaultdict(lambda: list(HTTP_ENCODINGS))


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
        if article.downloaded.structure_sketch is None:
            article.downloaded.structure_sketch = sketch_doc(article.downloaded.parsed_html)
            json_log(article_id=article_id, status='saved only')
        json_log(article_id=article_id, status='skipped')
        return

    time.sleep(random.random())
    domain = url.split('/', 3)[2]
    try:
        _, hops = article.download(url, accept_encodings=domain_encodings[domain])
    except FetchException as exc:
        hops = exc.hops
    else:
        exc = None

    _save_log(article, prior_status, hops, exc)


if __name__ == '__main__':
    main('fetch', download_and_save)
