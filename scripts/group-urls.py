#!/usr/bin/env python
"""
This script, given URLs from a domain from articleData.txt should find groups
that may constitute different types of (non-)content.
"""

from __future__ import print_function, division
import sys
import re
from collections import defaultdict, Counter
import random
MAX_DISPLAY = 10
counter = Counter()
grouped = defaultdict(set)
for l in sys.stdin:
    l = l.strip()
    url = l
    if '|' in l:
        l = l.split('|')[-1]
    if '://' not in l:
        continue

    url = re.sub('[0-9]', '0', url)
    if '?' in url:
        url, query = url.split('?', 1)
        query = '&'.join(x.split('=')[0] for x in query.split('&'))
    else:
        query = ''
    _, url = url.split('://', 1)
    if '/' in url:
        domain, path = url.split('/', 1)
    else:
        domain = url
        path = ''
    path = re.sub('[a-zA-Z-]+([0-9a-zA-Z-]*)', 'a', path)
    key = (path, query)
    group = grouped[key]
    if len(group) == MAX_DISPLAY:
        if random.random() > 1/MAX_DISPLAY:
            group.pop()
            group.add(l)
    else:
        group.add(l)
    counter[key] += 1


for key, count in counter.most_common():
    print(count, *key)
    lines = list(grouped[key])
    random.shuffle(lines)
    print('\n'.join(lines) + '\n')
