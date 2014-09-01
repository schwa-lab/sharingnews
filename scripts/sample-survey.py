
from __future__ import print_function
import glob
import os
import sys
import re
import urlparse
import tldextract
import datetime
import urllib
from xml.sax.saxutils import unescape as xml_unescape

now = datetime.datetime.now

COLUMNS = ['freq',
           'domain',
           'pattern',
           'qfields',
           'month',
           'start url',
           'end url',
           'canonical',
           'end status',
           'end MIME',
           'doc length']

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

    if not new_parse.netloc.startswith('<') and new_parse.port == old_parse.port == None:
        new_domain = tldextract.extract(new_parse.netloc)
        old_domain = tldextract.extract(old_parse.netloc)
        for f in old_domain._fields:
            new_f = getattr(new_domain, f)
            if new_f and new_f == getattr(old_domain, f):
                new_domain = new_domain._replace(**{f: '<{}>'.format(f)})
        new_domain = '.'.join(new_domain).replace('<domain>.<suffix>', '<domain+>')
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

    if old_parse.query and new_parse.query and not new_parse.query.startswith('<'):
        old_query = set(old_parse.query.split('&'))
        new_query = set(new_parse.query.split('&'))
        if new_query > old_query:
            new_parse = new_parse._replace(query='<query>' + '&' +
                                           '&'.join(sorted(map(urllib.urlencode, new_query - old_query))))

    out = new_parse.geturl()
    return out


CANONICAL_TAG_RE = re.compile(r'(?i)<link\b[^>]*\brel=.canonical[^>]*')
CANONICAL_URL_RE = re.compile(r'(?<=\bhref=["\']).*?(?=["\'])')

def parse(base, id):
    path = 'html-sample/{}/{}'.format(base, id)
    if not os.path.exists(path + '.stat'):
        return [''] * 5

    with open(path + '.stat') as stat_file:
        start_url = None
        for l in stat_file:
            if start_url is None:
                start_url = l.split('\t')[1]
        # Now have last line in l
        try:
            status, end_url, mime = l.rstrip('\n\r').split('\t')
        except NameError:
            status, end_url, mime = '-', '-', '-'
            start_url = '-'

    try:
        with open(path + '.html') as data_file:
            content = data_file.read()
            content = re.sub('<!--.*?-->', '', content).strip()
            length = len(content)
            canonical_link = CANONICAL_TAG_RE.search(content)
            if canonical_link:
                canonical = CANONICAL_URL_RE.search(canonical_link.group()).group()
                canonical = urlparse.urljoin(end_url, xml_unescape(canonical))
            else:
                canonical = '-'
    except IOError:
        canonical = '-'
        length = '-'

    if status.startswith('2') and end_url.count('/') <= 3:
        # Probably should have had 4xx code
        status += '?'
        # TODO: look for other such patterns

    return [url_as_diff(end_url, start_url), url_as_diff(canonical, end_url),
            status, mime, length]


for path in glob.glob('url-sample/*'):
    print(now(), path, file=sys.stderr)
    base = os.path.basename(path)
    with open('sample-survey/{}'.format(base), 'w') as out:
        for l in open(path):
            l = l.rstrip('\n\r')
            if not l:
                print(file=out)
                continue
            l = re.sub('\|.*\|', '\t', l).split('\t')
            l.extend(parse(base, l[5]))
            print(*l, sep='\t', file=out)
