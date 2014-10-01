from __future__ import print_function
import re
import urlparse
import sys
from xml.sax.saxutils import unescape as xml_unescape

import requests

HTTP_ENCODINGS = ('identity', 'deflate', 'compress', 'gzip')
meta_refresh_re = re.compile('<meta[^>]*?'
                             'content=["\']'
                             '([^>]+?url=(.*?))'
                             '["\'][^>]*', re.DOTALL | re.IGNORECASE)


class FetchException(Exception):
    def __init__(self, underlying, url, hops):
        super(FetchException, self).__init__(underlying)
        self.underlying = underlying
        self.exc_info = sys.exc_info()
        self.url = url
        self.hops = hops  # preceding the error, usually


def fetch_with_refresh(url, accept_encodings=HTTP_ENCODINGS, max_delay=20):
    try:
        hops = []
        refresh = True
        while refresh is not None:
            headers = {'accept-encoding': ', '.join(accept_encodings)}
            try:
                response = requests.get(url, timeout=10, headers=headers)
            except requests.exceptions.ContentDecodingError as e:
                enc = re.search('Received response with content-encoding: ([a-z]+),', repr(e))
                if not enc:
                    raise
                enc = enc.group(1)
                if enc not in accept_encodings:
                    raise
                print('>> Removing encoding {!r} for {!r}'.format(enc, url), file=sys.stderr)
                try:
                    accept_encodings.remove(enc)
                except AttributeError:
                    pass
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
                    if 'http-equiv="refresh' in tag \
                       or 'http-equiv=\'refresh' in tag:
                        refresh = match.group(1)

            if refresh is not None and refresh != response.url:
                delay, next_url = refresh.split(';', 1)
                _, next_url = next_url.split('=', 1)
                next_url = urlparse.urljoin(url, xml_unescape(next_url))
                assert next_url.startswith('http')
                if next_url in (hop.url for hop in hops):
                    break
                url = next_url
                if int(delay) > max_delay:
                    refresh = None
    except Exception as e:
        raise FetchException(e, url, hops)
    return hops


def get_mime(resp):
    return resp.headers.get('content-type', '').split(';')[0]

