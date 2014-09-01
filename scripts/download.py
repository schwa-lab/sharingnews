#!/usr/bin/env python
"""
Downloads URLs given file containing:

    path\turl

on each line.
"""
from __future__ import print_function
from collections import defaultdict
import requests
import os
import sys
import re
import datetime
import traceback
import urlparse
import random
import time
from xml.sax.saxutils import unescape as xml_unescape

now = datetime.datetime.now
PID = os.getpid()


def get_mime(resp):
    return resp.headers.get('content-type', '').split(';')[0]

COMMENTABLE_MIMES = ('html', 'xhtml', 'xml')


meta_refresh_re = re.compile('<meta[^>]*?content=["\']([^>]+?url=(.*?))["\'][^>]*', re.DOTALL | re.IGNORECASE)

def get_following_refresh(url, accept_encoding, max_delay=20):
    hops = []
    refresh = True
    while refresh is not None:
        try:
            response = requests.get(url, timeout=10, headers={'accept-encoding': ', '.join(accept_encoding)})
        except requests.exceptions.ContentDecodingError as e:
            enc = re.search('Received response with content-encoding: ([a-z]+),', repr(e))
            if not enc:
                raise
            enc = enc.group(1)
            if enc not in accept_encodings:
                raise
            print('>> Removing encoding {!r} for {!r}'.format(enc, url), file=sys.stderr)
            accept_encodings.remove(enc)
            continue
        hops.extend(response.history)
        hops.append(response)
        if response.status_code >= 400:
            break
        refresh = response.headers.get('refresh')
        if refresh is None:
            match = meta_refresh_re.search(response.content)
            if match is not None:
                tag = match.group(0).lower()
                if 'http-equiv="refresh' in tag or 'http-equiv=\'refresh' in tag:
                    refresh = match.group(1)

        if refresh is not None:
            delay, next_url = refresh.split(';', 1)
            _, next_url = next_url.split('=', 1)
            next_url = urlparse.urljoin(url, xml_unescape(next_url))
            assert next_url.startswith('http')
            if next_url in (hop.url for hop in hops):
                break
            url = next_url
            if int(delay) > max_delay:
                refresh = None
    return hops


path = None
skipped = 0
encodings = defaultdict(lambda: ['identity', 'deflate', 'compress', 'gzip'])
for i, l in enumerate(sys.stdin):
    if i % 100 == 0:
        print(PID, now(), 'Downloaded {}, skipped {}. Latest to {}'.format(i - skipped, skipped, path), file=sys.stderr)
    path, url = l.strip().split('\t')
    ts = now()
    if os.path.isfile(path + '.stat'):
        prev_stats = open(path + '.stat').readlines()
        if prev_stats and (prev_stats[-1].startswith('2') or prev_stats[-1].startswith('4')):
            skipped += 1
            continue
    with open(path + '.stat', 'w') as status_f:
        accept_encodings = encodings[urlparse.urlsplit(url).netloc]
        try:
            hops = get_following_refresh(url, accept_encodings)
        except Exception, e:
            print(type(e), url, '', file=status_f, sep='\t')
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
    time.sleep(random.random())
print(PID, now(), 'Downloaded {}, skipped {}. Done.'.format(i + 1 - skipped, skipped), file=sys.stderr)
