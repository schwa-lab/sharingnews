#!/usr/bin/env python

from __future__ import print_function, absolute_import, division
import argparse
import sys
import time
import random
from collections import defaultdict
import datetime
import traceback
import logging
import json
import pytz

import pika
import django
from bs4 import UnicodeDammit

from likeable.models import Article, DownloadedArticle
from likeable.scraping import (fetch_with_refresh, HTTP_ENCODINGS,
                               FetchException, get_mime)
from likeable.cleaning import compress_html, extract_canonical

django.setup()
now = lambda: datetime.datetime.utcnow().replace(tzinfo=pytz.utc)
logger = logging.getLogger(__file__)


domain_encodings = defaultdict(lambda: list(HTTP_ENCODINGS))


def json_log(**data):
    data['timestamp'] = now().isoformat()
    logger.info(json.dumps(data))


def enqueue(channel, queue, f):
    i = 0
    for l in f:
        i += 1
        channel.basic_publish(exchange='',
                              routing_key=queue,
                              body=str(int(l)),
                              properties=pika.BasicProperties(
                                  delivery_mode=2,  # make message persistent
                              ))
    json_log(enqueued=i)


def _save_article(article, response, timestamp):
    status = response.status_code
    if article.fetch_status != status:
        print('Replacing status {0.fetch_status} with {1} '
              'for {0.id}'.format(article, status))
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


def download_and_save(article_id):
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

    domain = url.split('/', 3)[2]
    timestamp = now()
    try:
        hops = fetch_with_refresh(url,
                                  accept_encodings=domain_encodings[domain])
    except FetchException as exc:
        hops = exc.hops
    else:
        exc = None

    if exc is None:
        _save_article(article, hops[-1], timestamp)
    # TODO: perhaps save pseudo-status on exception

    _save_log(article, prior_status, hops, exc)


def worker_callback(channel, method, properties, body):
    download_and_save(body)
    channel.basic_ack(delivery_tag=method.delivery_tag)
    time.sleep(random.random())


def worker(channel, queue):
    channel.basic_qos(prefetch_count=1)
    channel.basic_consume(worker_callback, queue=queue)
    print('Waiting for IDs to fetch. To exit press CTRL+C', file=sys.stderr)
    channel.start_consuming()


def main():
    import os
    import socket
    default_log_prefix = os.path.expanduser('~likeable/logs/fetch/'
                                            'fetch-{}-{}.log.bz2'
                                            ''.format(socket.gethostname(),
                                                      os.getpid()))
    ap = argparse.ArgumentParser()
    ap.add_argument('-H', '--host', default='localhost')
    ap.add_argument('--port', default=None)
    ap.add_argument('--queue', default='likeable-id-download')
    ap.add_argument('--log-path', default=default_log_prefix)
    subs = ap.add_subparsers()
    enqueue_ap = subs.add_parser('enqueue')
    enqueue_ap.set_defaults(app='enqueue')
    enqueue_ap.add_argument('-f', '--infile',
                            type=argparse.FileType('r'), default=sys.stdin,
                            help='Path where IDs are listed (default: STDIN)')
    worker_ap = subs.add_parser('worker')
    worker_ap.set_defaults(app='worker')
    args = ap.parse_args()

    logger.setLevel(logging.DEBUG)
    handler = logging.handlers.TimedRotatingFileHandler(args.log_path,
                                                        when='D',
                                                        encoding='bz2')
    print('Logging to', args.log_path + '*', file=sys.stderr)
    logger.addHandler(handler)

    conn_params = pika.ConnectionParameters(host=args.host, port=args.port)
    connection = pika.BlockingConnection(conn_params)
    channel = connection.channel()
    channel.queue_declare(queue=args.queue, durable=True)
    if args.app == 'worker':
        worker(channel, args.queue)
    else:
        enqueue(channel, args.queue, args.infile)
    connection.close()

if __name__ == '__main__':
    main()
