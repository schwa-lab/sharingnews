import re
import tldextract
import urlparse
import urllib
from xml.sax.saxutils import unescape as xml_unescape


DIGIT_RE = re.compile('[0-9]')
# Standard use of params would require ;, but /a=b/c=d is also used
PARAM_RE = re.compile('((?:;|^)[^=]+=)[^;/]*')
SLUG_CHARS = r'[\w\s\'",$+()-]'
SLUG_RE = re.compile(r'(?u){0}*[^\W\d]+{0}*'.format(SLUG_CHARS))
INT_ID_RE = re.compile(r'\b0+([,_.]0+)+\b|\b0{8}[0-]+\b')
# approximate RE for file extensions:
EXT_RE = re.compile(r'(.*)(\.[a-zA-Z]{1,5}[0-9]{0,2})$')


def url_signature(url):
    # TODO: doctests
    _, domain, path, query, _ = urlparse.urlsplit(url)
    query = '&'.join(urllib.unquote(x.split('=')[0]) for x in query.split('&'))
    path = urllib.unquote(path)
    ext_match = EXT_RE.search(path)
    if ext_match is None:
        ext = ''
    else:
        path, ext = ext_match.groups()
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
    return domain, path + ext, query


def strip_subdomains(domain):
    if '//' in domain:
        domain = domain.split('/', 3)[2]
    r = tldextract.extract(domain)
    if not r.suffix:
        return r.domain
    return '{}.{}'.format(r.domain, r.suffix)

CANONICAL_TAG_RE = re.compile(r'(?i)<link\b[^>]*\brel=.canonical[^>]*')
CANONICAL_URL_RE = re.compile(r'(?<=\bhref=["\']).*?(?=["\'])')


def extract_canonical(html, relative_to=None):
    canonical_link = CANONICAL_TAG_RE.search(html)
    if canonical_link:
        canonical = CANONICAL_URL_RE.search(canonical_link.group()).group()
        canonical = xml_unescape(canonical)
        if relative_to is not None:
            canonical = urlparse.urljoin(relative_to, canonical)
        return canonical
    else:
        return None


def url_as_diff(new, old):
    if new == old:
        return '<same>'
    if new == '-':
        return new
    old_parse = urlparse.urlsplit(old)
    new_parse = urlparse.urlsplit(new)

    changed = set()
    for f in old_parse._fields:
        new_f = getattr(new_parse, f)
        if new_f and new_f == getattr(old_parse, f):
            new_parse = new_parse._replace(**{f: '<{}>'.format(f)})
        elif new_f:
            changed.add(f)
    if tuple(changed) == ('scheme',):
        return '{}://<same>'.format(new_parse.scheme)

    if (not new_parse.netloc.startswith('<') and
            new_parse.port is None and old_parse.port is None):
        new_domain = tldextract.extract(new_parse.netloc)
        old_domain = tldextract.extract(old_parse.netloc)
        for f in old_domain._fields:
            new_f = getattr(new_domain, f)
            if new_f and new_f == getattr(old_domain, f):
                new_domain = new_domain._replace(**{f: '<{}>'.format(f)})
        new_domain = '.'.join(new_domain).replace('<domain>.<suffix>',
                                                  '<domain+>')
        new_parse = new_parse._replace(netloc=new_domain)

    if new_parse.path == old_parse.path + '/':
        new_parse = new_parse._replace(path='<path>/')
    if new_parse.path.startswith('/') and old_parse.path.startswith('/'):
        new_dirs = new_parse.path[1:].split('/')
        old_dirs = old_parse.path[1:].split('/')
        if new_dirs[-1] and new_dirs[-1] == old_dirs[-1]:
            new_dirs[-1] = '<basename>'
        old_dirs = {d: i for i, d in enumerate(old_dirs)}
        for i, new_dir in enumerate(new_dirs):
            if new_dir in old_dirs:
                new_dirs[i] = '<dir{}>'.format(old_dirs[new_dir] + 1)
        new_parse = new_parse._replace(path='/' + '/'.join(new_dirs))

    if (old_parse.query and new_parse.query and
            not new_parse.query.startswith('<')):
        old_query = set(old_parse.query.split('&'))
        new_query = set(new_parse.query.split('&'))
        if new_query > old_query:
            new_params = '&'.join(sorted(map(urllib.quote,
                                             new_query - old_query)))
            new_parse = new_parse._replace(query='<query>' + '&' + new_params)

    out = new_parse.geturl()
    return out
