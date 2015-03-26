import re
import tldextract
import urlparse
import urllib
from xml.sax.saxutils import escape as xml_escape
import HTMLParser
from bs4 import UnicodeDammit
xml_unescape = HTMLParser.HTMLParser().unescape


DIGIT_RE = re.compile('[0-9]')
# Standard use of params would require ;, but /a=b/c=d is also used
# PATH_PARAM_RE = re.compile('((?:;|/)[^=]+=)[^;/]*')  # for sub \1
SLUG_CHARS = r'[\w\s\'",$+()-]'
SLUG_RE = re.compile(r'(?u){0}*[^\W\d]+{0}*'.format(SLUG_CHARS))
INT_ID_RE = re.compile(r'\b\d+([,_.]+\d+)+\b|\b\d{8}[\d-]+\b')
# approximate RE for file extensions:
EXT_RE = re.compile(r'(\.[a-zA-Z]{1,30}[0-9]{0,2}[a-zA-Z]{0,4})$')
PATH_PARAM_RE = re.compile('=[^;/]*')  # for sub ''
PATHSIG_RE = re.compile('(?u)(?:'
                        '(?P<_ext>{EXT_RE.pattern})|'
                        '(?P<param>{PATH_PARAM_RE.pattern})|'
                        '(?P<slug>{SLUG_RE.pattern})|'
                        '(?P<id>{INT_ID_RE.pattern})|'
                        '(?P<digits>{DIGIT_RE.pattern}+)|'
                        '(?P<_other>.*?)'
                        ')'.format(**locals()))
QUERY_PARAM_RE = re.compile('=[^&]*')


def path_sig_cb(m, sub={'param': '', 'slug': 'a', 'id': 'ID'}):
    #print(m.group(), m.lastgroup)
    if m.lastgroup[0] == '_':
        return m.group()
    if m.lastgroup == 'digits':
        return '0' * (m.end() - m.start())

    return sub[m.lastgroup]


def url_signature(url):
    """
    >>> url_signature('http://www.people.com/people/package/0,,20395222,00.html')
    ('people.com', '/a/a/ID.html', '')
    """
    # TODO: doctests
    _, domain, path, query, _ = urlparse.urlsplit(url)
    path = PATH_PARAM_RE.sub('', path)
    # XXX: unquoting might invent extra '/'s
    path = urllib.unquote(path)
    try:
        path = PATHSIG_RE.sub(path_sig_cb, path.decode('utf8')).encode('utf8')
    except UnicodeDecodeError:
        path = PATHSIG_RE.sub(path_sig_cb, path)
    if domain.startswith('www.'):
        domain = domain[4:]
    query = QUERY_PARAM_RE.sub('', query)
    return domain, urllib.quote(path).replace('%3B', ';'), query


def strip_subdomains(domain):
    if '//' in domain:
        domain = domain.split('/', 3)[2]
    try:
        return strip_subdomains._cache[domain]
    except AttributeError:
        strip_subdomains._cache = {}
    except KeyError:
        pass
    r = tldextract.extract(domain)
    if r.suffix:
        out = '{}.{}'.format(r.domain, r.suffix)
    else:
        out = r.domain
    strip_subdomains._cache[domain] = out
    return out

OG_URL_TAG_RE = re.compile(r'(?i)<meta\b[^>]*\bproperty=.og:url[^>]*')
OG_URL_ATTR_RE = re.compile(r'(?i)\bcontent=(["\']|)(h.+?)\1(?:[\s>]|$)')
CANONICAL_TAG_RE = re.compile(r'(?i)<link\b[^>]*\brel=.canonical[^>]*')
CANONICAL_URL_RE = re.compile(r'(?i)\bhref=(["\']|)(h.+?)\1(?:[\s>]|$)')


def _extract_canonical(html, relative_to, tag_re, attr_re):
    canonical_link = tag_re.search(html)
    if canonical_link:
        tag = canonical_link.group()
        try:
            canonical = attr_re.search(tag).group(2)
        except AttributeError:
            return None
        canonical = xml_unescape(canonical)
        if relative_to is not None:
            canonical = urlparse.urljoin(relative_to, canonical)
        return canonical
    else:
        return None


def extract_canonical(html, relative_to=None):
    return _extract_canonical(html, relative_to, CANONICAL_TAG_RE, CANONICAL_URL_RE)


def extract_facebook_canonical(html, relative_to=None):
    canonical = _extract_canonical(html, relative_to, OG_URL_TAG_RE, OG_URL_ATTR_RE)
    if canonical is None:
        canonical = extract_canonical(html, relative_to)
    return canonical


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


SCRIPT_STYLE_RE = re.compile(r'<(script|style|iframe)\b.*?</\1\b.*?>', re.DOTALL | re.IGNORECASE)
WHITESPACE_RE = re.compile(r'[ \t]*(\n)[ \t]*(\n?)\s*', re.DOTALL)


def compress_html(html):
    """
    >>> compress_html('foo<script hello=world>foo </script>bar')
    'foobar'

    >>> compress_html('foo \\nbar')
    'foo\\nbar'
    >>> compress_html('foo  \\n  \\n  bar')
    'foo\\n\\nbar'
    >>> compress_html('foo \\n \\n \\n bar')
    'foo\\n\\nbar'

    ### >>> compress_html('foo<!-- hello world -->bar')
    ### 'foobar'
    """
    # remove <script/>, <style/>:
    # XXX: it's possible for </...> to appear inside a script or a textarea or an attr
    html = re.sub(SCRIPT_STYLE_RE, '', html)
    # remove comments (but these may be useful)
    ### html = re.sub(r'<!--.*?-->', '', html)
    # remove excess whitespace
    html = re.sub(WHITESPACE_RE, r'\1\2', html).strip()
    return html


def insert_base_href(html, url):
    match = re.search(r'(?i)<base[^>]*\bhref=(["\'])?(.*)?\1', html)
    if match is not None:
        url = urlparse.urljoin(url, xml_unescape(match.group(1)))
        html = re.sub(r'(?i)<base\b[^>]*>', '', html)
    html = re.sub('(<head[^>]*>)', r'\1<base href="{}">'.format(xml_escape(url)), html)
    return html


def unicode_from_www(response):
    override_encodings = []
    # Want different priorities to UnicodeDammit
    if 'content-type' in response.headers and ';' in response.headers['content-type']:
        override_encodings.append(response.encoding)
    match = re.search('(?i)<meta[^>]*http-equiv="content-type"[^>]*>', response.content)
    if match and ';' in match.group():
        # Ignore HTTP encoding
        override_encodings = []

    # FIXME: have found cases where XML comment contains bogus characters. Perhaps run over comment-stripped content.
    #        But have also found broken encoding in HTML attributes.

    # Smart quotes handling for Windows-12* encodings added 2015-03-04
    ud = UnicodeDammit(response.content, smart_quotes_to='html',
                       override_encodings=override_encodings,
                       is_html=True)
    # And an override if smart quotes are in UTF8 but it says ISO-8859
    if ud.original_encoding.lower().startswith('iso') and '\xe2\x80' in response.content:
        return response.content.decode('utf8', 'ignore')
    if ud.unicode_markup is None:
        raise UnicodeDecodeError('UnicodeDammit failed for '
                                 '{}'.format(response.url))
    return ud.unicode_markup
