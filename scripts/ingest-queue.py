import json
import itertools

import pika

from likeable.idqueue import main, json_log
from likeable.countapis import FBBatchFetcher, FB_URL_FIELDS


batch_fetcher = FBBatchFetcher(FB_URL_FIELDS)


def process(args, body):
    header, _, body = body.partition('\n')
    fields = header.split('|')
    url_field = fields.index('article_Url')
    body = [l.split('|') for l in body.split('\n')]
    # Perhaps begin by get-or-create sharewarsurl
    urls = [l[url_field] for l in body]
    fb_result = batch_fetcher.fetch_auto(urls)
    if not fb_result.startswith('{'):
        raise ValueError('Got result from FBBatchFetcher not beginning with')
    # Now create Article if necessary
    # Then wait for download cron (TBC) to run!
    fb_result = json.loads(fb_result)


def enqueue(args, channel, queue, f, header_lines=1, batch_size=50):
    i = 0
    header = ''.join(itertools.islice(f, header_lines))  # these precede every message
    batch = list(itertools.islice(f, batch_size))
    while batch:
        i += 1
        channel.basic_publish(exchange='',
                              routing_key=queue,
                              body=header + ''.join(batch),
                              properties=pika.BasicProperties(
                                  delivery_mode=2,  # make message persistent
                              ))
        batch = list(itertools.islice(f, batch_size))
    json_log(enqueued=i)


if __name__ == '__main__':
    main(process, enqueue=enqueue)
