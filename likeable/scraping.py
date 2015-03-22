from __future__ import print_function
import re
import urlparse
import sys
from xml.sax.saxutils import unescape as xml_unescape

from lxml import etree
from scrapy.selector import csstranslator
import requests

from .cache import lru_cache

css_to_xpath = csstranslator.ScrapyHTMLTranslator().css_to_xpath

HTTP_ENCODINGS = ('identity', 'deflate', 'compress', 'gzip')
meta_refresh_re = re.compile('<meta[^>]*?'
                             'content=["\']'
                             '([^>]+?url=([^>]*?))'
                             '["\'][^>]*', re.DOTALL | re.IGNORECASE)


class FetchException(Exception):
    def __init__(self, underlying, url, hops, code=None):
        super(FetchException, self).__init__(underlying)
        self.underlying = underlying
        self.exc_info = sys.exc_info()
        self.url = url
        self.hops = hops  # preceding the error, usually
        if code is None:
            if isinstance(underlying, requests.TooManyRedirects):
                code = -1
            if isinstance(underlying, requests.Timeout):
                code = -10
        self.code = code


USER_AGENTS = {
    'fb': 'facebookexternalhit/1.1 (+http(s)://www.facebook.com/externalhit_uatext.php)',
}


def fetch_with_refresh(url, accept_encodings=HTTP_ENCODINGS, max_delay=20, user_agent_spoof=None):
    try:
        hops = []
        refresh = True
        while refresh is not None:
            headers = {'accept-encoding': ', '.join(accept_encodings or HTTP_ENCODINGS)}
            if user_agent_spoof is not None:
                headers['User-Agent'] = USER_AGENTS[user_agent_spoof]
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
            print('>', response, 'to', url)
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
    if hops[-1].status_code == 200 and not hops[-1].content:
        raise FetchException('Status 200 but empty content', url, hops, code=-2)
    return hops


def get_mime(resp):
    return resp.headers.get('content-type', '').split(';')[0].strip().lower()


def _node_text(node, _extractor=etree.XPath('.//text() | .//br')):
    if not hasattr(node, 'tag'):
        return unicode(node)
    return u''.join(re.sub(u'[\n\r ]+', ' ', unicode(el)) if not hasattr(el, 'tag') else u'\n'
                    for el in _extractor(node)).strip()


def readability_summarise_tree(tree):
    import readability
    doc = readability.Document(etree.tounicode(tree))
    summ = doc.summary()
    return etree.fromstring(summ, parser=etree.HTMLParser())


DEFAULT_CODE = '<default>'
DOMAIN_DEFAULT_CODE = '<domain>'
TEXT_CODE = '((text))'
READABILITY_SUMMARY_CODE = '((readability.summary))'
XPATH_CODE = '((xpath))'


@lru_cache(maxsize=1024)
def _get_extractor(selector):
    if not selector.strip():
        return None, False
    preprocessor = None
    is_text = selector.startswith(TEXT_CODE)
    if is_text:
        selector = selector[len(TEXT_CODE):].strip()
    if selector.startswith(READABILITY_SUMMARY_CODE):
        selector = selector[len(READABILITY_SUMMARY_CODE):].strip()
        preprocessor = readability_summarise_tree

    if not selector:
        # Applies in special case due to control codes
        xpath = lambda node: node
    elif selector.startswith(XPATH_CODE):
        xpath = etree.XPath(selector[len(XPATH_CODE):])
    else:
        xpath = etree.XPath(css_to_xpath(selector))

    if preprocessor:
        extractor = lambda doc: xpath(preprocessor(doc))
    else:
        extractor = xpath
    return extractor, is_text


def extract(selector, doc=None, as_unicode=False, return_which=False):
    extractions = None
    if not selector:
        return
    selector = re.sub(r'\(\(comment.*?\)\)', '', selector)
    if selector.startswith(DOMAIN_DEFAULT_CODE):
        selector = selector[len(DOMAIN_DEFAULT_CODE):].strip()
    if selector.startswith(DEFAULT_CODE):
        selector = selector[len(DEFAULT_CODE):].strip()
    which = None
    for i, selector in enumerate(selector.split(';')):  # TODO: handle semicolon in string
        extractor, is_text = _get_extractor(selector.strip())
        if doc is None:
            # Just caching
            continue
        if extractor is None:
            continue
        extractions = extractor(doc)
        if is_text:
            extractions = [_node_text(el) for el in extractions]
        if as_unicode:
            extractions = [etree.tounicode(el) if hasattr(el, 'tag') else unicode(el)
                           for el in extractions]
            if as_unicode == 'join':
                extractions = '\n'.join(extractions)
                if not extractions.strip():
                    extractions = None
            elif not any(e.strip() for e in extractions):
                extractions = []
        if extractions:
            which = i
            break
    if return_which:
        return extractions, which
    return extractions
