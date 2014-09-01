
from __future__ import print_function
import glob
import os
import sys
import re
import datetime

from likeable_scrapy.cleaning import (extract_canonical, url_as_diff,
                                      url_signature, strip_subdomains)

###DATA_ROOT = os.path.expanduser('~likeable/data')
DATA_ROOT = os.path.expanduser('./data')

now = datetime.datetime.now

COLUMNS = ['id',
           'date',
           'start url',
           'start domain',
           'start sig',
           'end url',  # with canonicalisation
           'end domain',
           'end sig',
           'status',
           'MIME',
           'length',
           ]


def fmt_signature(url):
    return '{}{}?{}'.format(*url_signature(url))


def parse(stat_path):
    with open(stat_path) as stat_file:
        lines = [l.rstrip('\n\r').split('\t') for l in stat_file]
    try:
        start_url = lines[0][1]
        status, end_url, mime = lines[-1]
    except IndexError:
        start_url, status, end_url, mime = '----'

    try:
        with open(os.path.splitext(stat_path)[0] + '.html') as data_file:
            content = data_file.read()
            content = re.sub('<!--.*?-->', '', content).strip()
            length = len(content)
            canonical = extract_canonical(content, end_url) or '-'
    except IOError:
        canonical = '-'
        length = '-'

    if status.startswith('2') and end_url.count('/') <= 3 and '?' not in end_url:
        # Probably should have had 4xx code
        status += '?'
        # TODO: look for other such patterns

    canonical_url = end_url if canonical == '-' else canonical

    if start_url != '-':
        start_domain = strip_subdomains(start_url)
    else:
        start_domain = '-'
    start_sig = fmt_signature(start_url)
    if canonical_url == start_url:
        end_diff = '<same>'
        end_domain = start_domain
        end_sig = start_sig
    else:
        end_diff = url_as_diff(canonical_url, start_url)
        end_domain = strip_subdomains(canonical_url)
        end_sig = fmt_signature(canonical_url)
    return [start_url, start_domain, start_sig,
            end_diff, end_domain, end_sig,
            status, mime, length]


date_lookup = {l.split('|')[0]: l.split('|')[1].split()[0]
               for l in open(os.path.join(DATA_ROOT, 'articleData.txt'))
               if '|http' in l}

print(now(), 'Loaded date lookup of', len(date_lookup), 'entries',
      file=sys.stderr)

for path in glob.glob(os.path.join(DATA_ROOT, 'html-sample/*/*.stat')):
    #print(now(), path, file=sys.stderr)
    l = parse(path)
    url_id = os.path.splitext(os.path.basename(path))[0]
    print(url_id, date_lookup[url_id], *l, sep='\t')
