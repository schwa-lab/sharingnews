import re
import tldextract
import urlparse
import urllib


DIGIT_RE = re.compile('[0-9]')
# Standard use of params would require ;, but /a=b/c=d is also used
PARAM_RE = re.compile('((?:;|^)[^=]+=)[^;/]*')
SLUG_CHARS = r'[\w\'",$+()-]'
SLUG_RE = re.compile(r'(?u){0}*[^\W\d]+{0}*'.format(SLUG_CHARS))
INT_ID_RE = re.compile(r'\b0+([,_.]0+)+\b|\b0{8}[0-]+\b')

def url_signature(url):
    # TODO: doctests
    _, domain, path, query, _ = urlparse.urlsplit(url)
    query = '&'.join(urllib.unquote(x.split('=')[0]) for x in query.split('&'))
    path = urllib.unquote(path)
    path = DIGIT_RE.sub('0', path)
    # XXX: unquoting might invent extra '/'s
    path = '/'.join(urllib.unquote(PARAM_RE.sub(r'\1', part))
                    for part in path.split('/'))
    try:
        path = SLUG_RE.sub('a', path.decode('utf8')).encode('utf8')
    except UnicodeDecodeError:
        path = SLUG_RE.sub('a', path)
    path = INT_ID_RE.sub('ID', path)
    if domain.startswith('www.'):
        domain = domain[4:]
    return domain, path, query


def strip_subdomains(domain):
    r = tldextract.extract(domain)
    if not r.suffix:
        return r.domain
    return '{}.{}'.format(r.domain, r.suffix)
