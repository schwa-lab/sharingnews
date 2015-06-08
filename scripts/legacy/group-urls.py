#!/usr/bin/env python
"""
This script, given URLs from a domain from articleData.txt should find groups
that may constitute different types of (non-)content.
"""

from __future__ import print_function, division
import sys
from collections import defaultdict, Counter
import random

from likeable.cleaning import url_signature

MAX_DISPLAY = 10
counter = Counter()
grouped = defaultdict(set)

for l in sys.stdin:
    l = l.strip()
    url = l
    if '://' not in l:
        continue

    key = url_signature(l)
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
