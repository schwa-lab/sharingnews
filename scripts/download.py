#!/usr/bin/env python
"""
Downloads URLs given file containing:

    path\turl

on each line.
"""
from __future__ import print_function
import requests
import sys
import datetime

now = datetime.datetime.now


def get_mime(resp):
    return resp.headers.get('content-type', '')

COMMENTABLE_MIMES = ('html', 'xhtml', 'xml')


for l in sys.stdin:
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
                  '<!-- requested at {} from {}'
                  '     response in {}s from {} -->'
                  ''.format(ts, url, response.elapsed, response.url),
                  file=content_f)
