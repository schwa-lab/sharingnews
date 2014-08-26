#!/usr/bin/env python
"""
Downloads URLs given file containing:

    path\turl

on each line.
"""
from __future__ import print_function
import requests
import os
import sys
import datetime

now = datetime.datetime.now
PID = os.getpid()


def get_mime(resp):
    return resp.headers.get('content-type', '').split(';')[0]

COMMENTABLE_MIMES = ('html', 'xhtml', 'xml')


path = None
for i, l in enumerate(sys.stdin):
    if i % 100 == 0:
        print(PID, now(), 'Downloaded {}. Latest to {}'.format(i + 1, path), file=sys.stderr)
    path, url = l.strip().split('\t')
    ts = now()
    with open(path + '.stat', 'w') as status_f:
        try:
            response = requests.get(url)
        except Exception, e:
            print(type(e), url, '', file=status_f, sep='\t')
            continue
        for hist_resp in response.history + [response]:
            print(hist_resp.status_code, hist_resp.url,
                  get_mime(hist_resp),
                  file=status_f, sep='\t')

    with open(path + '.html', 'w') as content_f:
        content_f.write(response.content)
        if get_mime(response).split('/')[-1].lower() in COMMENTABLE_MIMES:
            print('\n'
                  '<!-- requested at {} from {}\n'
                  '     response in {}s from {} -->'
                  ''.format(ts, url, response.elapsed, response.url),
                  file=content_f)
print(PID, now(), 'Downloaded {}. Done.'.format(i), file=sys.stderr)
