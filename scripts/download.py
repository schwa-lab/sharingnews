#!/usr/bin/env python
"""
Downloads URLs given file containing:

    path\turl

on each line.


DEPRECATED
"""
from __future__ import print_function
from collections import defaultdict
import os
import sys
import datetime
import traceback
import urlparse
import random
import time

from likeable.scraping import fetch_with_refresh, get_mime

now = datetime.datetime.now
PID = os.getpid()


COMMENTABLE_MIMES = ('html', 'xhtml', 'xml')


def download(url, path):
    ts = now()
    if os.path.isfile(path + '.stat'):
        prev_stats = open(path + '.stat').readlines()
        if prev_stats and (prev_stats[-1].startswith('2') or prev_stats[-1].startswith('4')):
            return False
    with open(path + '.stat', 'w') as status_f:
        accept_encodings = encodings[urlparse.urlsplit(url).netloc]
        try:
            hops = fetch_with_refresh(url, accept_encodings)
        except Exception, e:
            print('<{}>'.format(repr(e)), url, '', file=status_f, sep='\t')
            print('ERROR processing', l, file=sys.stderr)
            traceback.print_exc(file=sys.stderr)
            continue
        except KeyboardInterrupt, e:
            print(type(e), url, '', file=status_f, sep='\t')
            raise
        for hop in hops:
            print(hop.status_code, hop.url, get_mime(hop),
                  file=status_f, sep='\t')

    response = hops[-1]
    with open(path + '.html', 'w') as content_f:
        content_f.write(response.content)
        if get_mime(response).split('/')[-1].lower() in COMMENTABLE_MIMES:
            print('\n'
                  '<!-- requested at {} from {}\n'
                  '     response in {}s from {} -->'
                  ''.format(ts, url, response.elapsed, response.url),
                  file=content_f)
    return True


path = None
skipped = 0
encodings = defaultdict(lambda: ['identity', 'deflate', 'compress', 'gzip'])
for i, l in enumerate(sys.stdin):
    if i % 100 == 0:
        print(PID, now(), 'Downloaded {}, skipped {}. Latest to {}'.format(i - skipped, skipped, path), file=sys.stderr)
    path, url = l.strip().split('\t')
    success = download(url, path)
    skipped += not success
    time.sleep(random.random())
print(PID, now(), 'Downloaded {}, skipped {}. Done.'.format(i + 1 - skipped, skipped), file=sys.stderr)
