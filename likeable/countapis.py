# TODO: note example responses
# TODO: wrap for multiple URLs, error-resilience, consistent response format
# TODO: raw fetches for facebook batch, linkedin, G+, etc. See https://gist.github.com/jonathanmoore/2640302
from __future__ import print_function, division
import requests
import time
import functools
import sys
import datetime
import re
import urllib
import json

now = datetime.datetime.now

from .secret import FB_API_TOKEN


def _str_to_list(obj):
    if isinstance(obj, (str, unicode, bytes)):
        return [obj]
    return list(obj)


# UNDERLYING API CALLS

def fetch_twitter(url):
    return requests.get('http://urls.api.twitter.com/1/urls/count.json', params={'url': url})


def fetch_facebook_rest(urls):
    return requests.get('http://api.ak.facebook.com/restserver.php',
                        params={'v': '1.0',
                                'method': 'links.getStats',
                                'format': 'json',
                                'urls': ','.join(urls)})


def fetch_facebook_ids(urls):
    if len(urls) > 50:
        raise ValueError('Facebook Graph API limits multiple ID requests to 50')
    return requests.get('https://graph.facebook.com/v2.2', params={'access_token': FB_API_TOKEN,
                                                                   'ids': ','.join(urls)})


def retry_until_success(fn=None, retries=10, wait=1):
    if fn is None:
        return functools.partial(retry_until_success, retries=retries, wait=wait)

    @functools.wraps(fn)
    def wrapper(*args, **kwargs):
        remaining = retries
        resp = fn(*args, **kwargs)
        while retries and resp.status_code >= 400:
            time.sleep(wait)
            resp = fn(*args, **kwargs)
            remaining -= 1
        return resp
    return wrapper


# Batch fetch from Facebook API
COMMA_RE = re.compile(',|%2[cC]')
RETRY_ERRORS = [-2, -1, 2, 4, 17, 341]  # 1 ; -1 is our own
FAIL_ERRORS = [102, 10, 1609005]
ERROR_CODE_RE = re.compile(r'"error".*"code":\s*([0-9])', re.DOTALL)

class FBAPIError(Exception):
    pass

FB_URL_FIELDS = 'og_object{id,title,url,created_time,updated_time},share'

class FBBatchFetcher(object):
    # XXX: hacky
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

    def fetch_auto(self, urls):
        if COMMA_RE.search(''.join(urls)):
            return self.fetch_batch(urls)
        return self.fetch_comma(urls)

    def fetch_comma(self, urls, _depth=1):
        if not urls:
            return '{}'
        self._pre()
        try:
            resp = requests.get('https://graph.facebook.com/v2.2?access_token={}&ids={}'.format(FB_API_TOKEN, ','.join(urllib.quote(url) for url in urls)),
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
                    print(now(), 'Wait is now {} with error:\n{}\n\nURLS: {}'.format(self.wait, out, urls), file=sys.stderr)
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
        if not urls:
            return '{}'
        self._pre()
        if self.params:
            params = '?' + urllib.urlencode(self.params)
        else:
            params = ''
        batch = '[{}]'.format(','.join(self.BATCH_FMT % json.dumps(urllib.quote(url) + params)
                                       for url in urls))
        try:
            resp = requests.post('https://graph.facebook.com/v2.2',
                                 data={'access_token': FB_API_TOKEN,
                                       'include_headers': 'false',
                                       'batch': batch},
                                 timeout=50)
        except (requests.Timeout, requests.ConnectionError) as e:
            print(now(), repr(e), file=sys.stderr)
            if _depth == self.MAX_CONTIGUOUS_FAILURE:
                raise
            return self.fetch_batch(urls, _depth=_depth + 1)
        resp = resp.json()
        assert len(urls) == len(resp), resp
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
