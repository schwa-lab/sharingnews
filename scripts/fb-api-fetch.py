#!/usr/bin/env python
from __future__ import print_function, division

import urllib
import sys
import re
import time
import datetime
import json
from itertools import islice

import requests

now = datetime.datetime.now

ACCESS_TOKEN = '1542059102694981|snItY58M0f9cwDP0OFECJRsEkKE'  # from facebook.get_app_access_token == grant_type=client_credentials


RETRY_ERRORS = [-2, -1, 2, 4, 17, 341]  # 1 ; -1 is our own
FAIL_ERRORS = [102, 10, 1609005]
ERROR_CODE_RE = re.compile(r'"error".*"code":\s*([0-9])', re.DOTALL)


ID_RE = re.compile('^[0-9]+$')

class FBAPIError(Exception):
    pass


class Fetcher(object):
    def __init__(self, fields=None, wait=1e-9):
        if fields:
            self.params = {'fields': fields}
        else:
            self.params = None
        self.wait = wait
        self.n_reqs = 0
        self.n_success = 0
        self.start_time = time.time()
        self.n_report = 5

    MAX_WAIT = 1
    MAX_CONTIGUOUS_FAILURE = 20

    def _pre(self):
        if self.n_reqs == self.n_report:
            print(now(), 'Made {} requests with wait={:g}s. Success rate: {:.1f}%; {:.1f}s per success'.format(self.n_reqs, self.wait, 100 * self.n_success / self.n_reqs, (time.time() - self.start_time) / self.n_success if self.n_success else 0), file=sys.stderr)
            if self.n_report > 500:
                self.n_report += 500
            else:
                self.n_report += self.n_report
        time.sleep(self.wait)
        self.n_reqs += 1

    def fetch_comma(self, urls, _depth=1):
        self._pre()
        try:
            resp = requests.get('https://graph.facebook.com/v2.1?access_token={}&ids={}'.format(ACCESS_TOKEN, ','.join(urllib.quote(url) for url in urls)),
                                params=self.params, timeout=30)
        except (requests.Timeout, requests.ConnectionError) as e:
            code = -1
            out = repr(e)
        else:
            out = resp.content
            err = ERROR_CODE_RE.search(out)
            code = None if err is None else int(err.group(1))
        if code is not None:
            if (code == 1 or code not in RETRY_ERRORS or _depth == self.MAX_CONTIGUOUS_FAILURE // 2):
                # backoff
                return self.fetch_batch(urls)
            if _depth == self.MAX_CONTIGUOUS_FAILURE:
                raise RuntimeError('{} contiguous failures: code {}'.format(_depth, code))
            if code in RETRY_ERRORS:
                print(now(), 'Retrying with longer wait after error', code, file=sys.stderr)
                self.wait *= 2
                if self.wait > self.MAX_WAIT:
                    raise RuntimeError('Wait is now {} which exceeds maximum of {}'.format(self.wait, self.MAX_WAIT))
                if _depth and _depth % 4 == 0:
                    print(now(), 'Wait is now {} with error:\n{}'.format(self.wait, out), file=sys.stderr)
                    time.sleep(20)
                return self.fetch_comma(urls, _depth=_depth + 1)
            if code == 1:
                w = 5 * (_depth + 1)
                print(now(), 'Waiting {}s after code {}'.format(w, code), file=sys.stderr)
                time.sleep(w)
                return self.fetch_comma(urls, _depth=_depth + 1)
            else:
                raise FBAPIError('Error returned from FB Graph API:\n' + out)
        self.n_success += 1
        return out

    BATCH_FMT = '{"method":"GET","relative_url":%s}'

    def fetch_batch(self, urls, _depth=1):
        self._pre()
        batch = '[{}]'.format(','.join(self.BATCH_FMT % json.dumps(url)
                                       for url in urls))
        try:
            resp = requests.post('https://graph.facebook.com/v2.1',
                                 data={'access_token': ACCESS_TOKEN,
                                       'include_headers': 'false',
                                       'batch': batch},
                                 timeout=50)
        except (requests.Timeout, requests.ConnectionError) as e:
            print(now(), repr(e), file=sys.stderr)
            if _depth == self.MAX_CONTIGUOUS_FAILURE:
                raise
            return self.fetch_batch(urls, _depth=_depth + 1)
        resp = resp.json()
        assert len(urls) == len(resp)
        errors = []
        out = ['{']
        for url, entry in zip(urls, resp):
            if entry is None:
                # FIXME: should retry straight away?
                body = 'null'
            else:
                body = entry[u'body']
            out.extend([json.dumps(url), ':', body, ','])
            if u'"error":' in body:
                errors.append((url, json.loads(body)))
        if len(errors) == len(urls):
            if _depth and _depth % 4 == 0:
                time.sleep(30)
            if _depth == self.MAX_CONTIGUOUS_FAILURE:
                raise RuntimeError('{} contiguous failures:'.format(_depth))
            # no successes
            print(now(), 'Retrying with longer wait after all failed with error', *errors,
                  file=sys.stderr, sep='\n')
            self.wait *= 2
            return self.fetch_batch(urls, _depth=_depth + 1)
        if out[-1] == '{':
            out.append('}')
        elif out[-1] == ',':
            out[-1] = '}'
        self.n_success += 1
        return ''.join(out)

def iter_lines(f, resume=None):
    seen = set()
    for l in f:
        if resume is not None:
            if l.rstrip('\n\r') == resume:
                print(now(), 'Resuming at', resume, file=sys.stderr)
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
    ap.add_argument('--comma', default=False, action='store_true',
                    help='Use FB Graph API\'s comma-based multiple-ID syntax')
    ap.add_argument('-b', '--batch-size', default=24, type=int)
    ap.add_argument('-f', '--fields', default=None,
                    help='Select only these fields. E.g. '
                         'id,created_time,type,image,site_name,data,video')
    args = ap.parse_args()

    if args.fields is not None and not args.comma:
        ap.error('Require --comma to use fields')
    getter = Fetcher(fields=args.fields)
    print(now(), 'Reading from stdin with resume at', args.resume, file=sys.stderr)
    url_iter = iter_lines(sys.stdin, args.resume)
    urls = list(islice(url_iter, args.batch_size))
    fetch = getter.fetch_comma if args.comma else getter.fetch_batch
    while urls:
        try:
            print(fetch(urls))
        except:
            print(now(), 'While fetching:', urls, sep='\n', file=sys.stderr)
            raise
        urls = list(islice(url_iter, args.batch_size))
