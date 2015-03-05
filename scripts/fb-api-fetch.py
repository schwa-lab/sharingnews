#!/usr/bin/env python
from __future__ import print_function, division

import sys
import re
import datetime
from itertools import islice
from likeable.countapis import FBBatchFetcher, FB_URL_FIELDS

now = datetime.datetime.now


ID_RE = re.compile('^[0-9]+$')

def iter_lines(f, resume=None):
    seen = set()
    for i, l in enumerate(f):
        if resume is not None:
            if l.rstrip('\n\r') == resume:
                print(now(), 'Resuming at', resume, 'on line', i + 1, file=sys.stderr)
                resume = None
            else:
                continue
        if l.startswith('#') or l in seen:
            continue
        seen.add(l)
        l = l.rstrip('\n\r')
        assert l.startswith('http') or ID_RE.match(l)
        yield l

if __name__ == '__main__':
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument('-r', '--resume', default=None,
                    help='Skip input until this entry is read')
    ap.add_argument('--auto', dest='mode', action='store_const', const='auto', default='auto',
                    help='Decide between batch and comma-sep mode')
    ap.add_argument('--batch', dest='mode', action='store_const', const='batch',
                    help='Always use batch queries')
    ap.add_argument('--comma', dest='mode', action='store_const', const='comma',
                    help='Always use comma-delimited queries')
    ap.add_argument('-b', '--batch-size', default=24, type=int)
    ap.add_argument('-f', '--fields', default=FB_URL_FIELDS,
                    help='Select only these fields. E.g. '
                         'id,created_time,type,image,site_name,data,video')
    args = ap.parse_args()

    getter = FBBatchFetcher(fields=args.fields)
    print(now(), 'Reading from stdin with resume at', args.resume, file=sys.stderr)
    url_iter = iter_lines(sys.stdin, args.resume)
    urls = list(islice(url_iter, args.batch_size))
    fetch = getattr(getter, 'fetch_' + args.mode)
    while urls:
        try:
            print(fetch(urls))
        except:
            print(now(), 'While fetching:', urls, sep='\n', file=sys.stderr)
            raise
        urls = list(islice(url_iter, args.batch_size))
