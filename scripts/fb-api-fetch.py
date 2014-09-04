from __future__ import print_function, division

import urllib
import sys
import re
import time
import datetime
from itertools import islice

import requests

now = datetime.datetime.now

ACCESS_TOKEN = '1542059102694981|snItY58M0f9cwDP0OFECJRsEkKE'  # from facebook.get_app_access_token == grant_type=client_credentials


RETRY_ERRORS = [2, 4, 17, 341]  # 1
FAIL_ERRORS = [102, 10, 1609005]
ERROR_CODE_RE = re.compile(r'"error".*"code":\s*([0-9])', re.DOTALL)

class FBAPIError(Exception):
    pass


BATCH_SIZE = 24


class Getter(object):
    def __init__(self, wait=1e-9):
        self.wait = wait
        self.n_reqs = 0
        self.n_success = 0
        self.start_time = time.time()
        self.n_report = 5

    MAX_WAIT = 1
    MAX_CONTIGUOUS_FAILURE = 10

    def get(self, urls, _depth=1):
        if self.n_reqs == self.n_report:
            print(now(), 'Made {} requests with wait={:g}s. Success rate: {:.1f}%; {:.1f}s per success'.format(self.n_reqs, self.wait, 100 * self.n_success / self.n_reqs, (time.time() - self.start_time) / self.n_success), file=sys.stderr)
            self.n_report += self.n_report
            if self.n_report > 5000:
                self.n_report += 5000
        time.sleep(self.wait)
        self.n_reqs += 1
        resp = requests.get('https://graph.facebook.com/v2.1?access_token={}&ids={}'.format(ACCESS_TOKEN, ','.join(urllib.quote(url) for url in urls)),
                            timeout=30)
        out = resp.content
        err = ERROR_CODE_RE.search(out)
        if err is not None:
            if _depth == self.MAX_CONTIGUOUS_FAILURE:
                raise RuntimeError('{} contiguous failures'.format(_depth))
            code = int(err.group(1))
            if code in RETRY_ERRORS:
                print('Retrying with longer wait after error', code, file=sys.stderr)
                self.wait *= 2
                if self.wait > self.MAX_WAIT:
                    raise RuntimeError('Wait is now {} which exceeds maximum of {}'.format(self.wait, self.MAX_WAIT))
                if _depth > 2:
                    print(now(), 'Wait is now {} with error:\n{}'.format(self.wait, out), file=sys.stderr)
                return self.get(urls, _depth=_depth + 1)
            if code == 1:
                w = 5 * (_depth + 1)
                print(now(), 'Waiting {}s after code {}'.format(w, code), file=sys.stderr)
                time.sleep(w)
                return self.get(urls, _depth=_depth + 1)
            else:
                raise FBAPIError('Error returned from FB Graph API:\n' + out)
        self.n_success += 1
        return out

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
        assert l.startswith('http')
        yield l

if __name__ == '__main__':
    getter = Getter()
    resume = sys.argv[1] if len(sys.argv) > 1 else None
    print(now(), 'Reading from stdin with resume at', resume, file=sys.stderr)
    url_iter = iter_lines(sys.stdin, resume)
    urls = list(islice(url_iter, BATCH_SIZE))
    while urls:
        try:
            print(getter.get(urls))
        except:
            print('While fetching:', urls, sep='\n', file=sys.stderr)
            raise
        urls = list(islice(url_iter, BATCH_SIZE))
