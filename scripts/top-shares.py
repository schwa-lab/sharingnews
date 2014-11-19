#!/usr/bin/env python
from __future__ import print_function, division

import argparse
import sys
import csv
import codecs
import StringIO

import django
django.setup()

from likeable.models import Article


class UnicodeWriter:
    """
    A CSV writer which will write rows to CSV file "f",
    which is encoded in the given encoding.

    Derived from https://docs.python.org/2/library/csv.html#csv-examples
    """

    def __init__(self, f, dialect=csv.excel, encoding="utf-8", **kwds):
        # Redirect output to a queue
        self.queue = StringIO.StringIO()
        self.writer = csv.writer(self.queue, dialect=dialect, **kwds)
        self.stream = f
        self.encoder = codecs.getincrementalencoder(encoding)()

    def writerow(self, row):
        self.writer.writerow([s.encode("utf-8") if hasattr(s, 'encode') else str(s) for s in row])
        # Fetch UTF-8 output from the queue ...
        data = self.queue.getvalue()
        data = data.decode("utf-8")
        # ... and reencode it into the target encoding
        data = self.encoder.encode(data)
        # write to the target stream
        self.stream.write(data)
        # empty queue
        self.queue.truncate(0)

    def writerows(self, rows):
        for row in rows:
            self.writerow(row)


if __name__ == '__main__':
    ap = argparse.ArgumentParser()
    ap.add_argument('-n', '--limit', type=int, help='Number of top entries')
    ap.add_argument('-t', '--cutoff', type=int, help='Get all entries with counts above this number')
    ap.add_argument('-d', '--domain', help='Base domain to query')
    args = ap.parse_args()

    articles = Article.objects
    if getattr(args, 'cutoff', None) is not None:
        articles = articles.filter(total_shares__gt=args.cutoff)
    if getattr(args, 'domain', None) is not None:
        articles = articles.filter(url_signature__base_domain=args.domain)

    articles = articles.filter(total_shares__isnull=False)
    articles = articles.order_by('-total_shares')
    articles = articles.values_list('url', 'total_shares', 'id',
                                    'url_signature__base_domain', 'fb_created',
                                    'title', 'description')

    if getattr(args, 'limit', None) is not None:
        articles = articles[:args.limit]

    writer = UnicodeWriter(sys.stdout, dialect='excel-tab')

    writer.writerow(['url', 'total-shares', 'facebook-id', 'base-domain',
                     'facebook-created', 'title', 'description'])
    writer.writerows(articles)
