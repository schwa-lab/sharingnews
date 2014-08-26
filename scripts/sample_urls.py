#!/usr/bin/env python
"""
Samples from article data such that there is one instance of every
(domain, URL shape, month) present for frequent URL shapes.
"""
from __future__ import print_function, division

import os
import sys
from collections import defaultdict
import random
import datetime
from likeable_scrapy.cleaning import url_signature

MIN_CLUSTER_SIZE = 30
now = datetime.datetime.now
random = random.Random(0)  # allow some reproducability

out_dir = sys.argv[1]
assert not os.path.exists(out_dir)

sample = defaultdict(lambda: defaultdict(lambda: (0, '')))
for i, l in enumerate(sys.stdin):
    if i % 100000 == 0:
        print(now(), 'Sampled from {}'.format(i), file=sys.stderr)
    if '|' not in l or '://' not in l:
        continue
    l = l.rstrip()
    mo = l.split('|')[1].rsplit('-', 1)[0]
    sig = url_signature(l)
    sig_data = sample[sig]
    count, url = sig_data[mo]
    if not count or random.random() > 1 / (count + 1):
        url = l
    sig_data[mo] = (count + 1, url)

print(now(), 'Sampled from {}. Writing to {}.'.format(i, out_dir),
      file=sys.stderr)

sample = [(sum(count for count, url in sig_data.itervalues()), sig, sig_data)
          for sig, sig_data in sample.iteritems()]
sample = [tup for tup in sample if tup[0] >= MIN_CLUSTER_SIZE]
sample.sort(reverse=True)
n_items = 0
os.mkdir(out_dir)
for freq, (domain, pattern, query_params), sig_data in sample:
    n_items += len(sig_data)
    with open('{}/{}'.format(out_dir, domain), 'a') as hist_f:
        #print(freq, domain, pattern, query_params,
        #      file=hist_f, sep='\t')
        for mo, (mo_freq, inst) in sorted(sig_data.items()):
            print(mo_freq, domain, pattern, query_params,
                  mo, inst, file=hist_f, sep='\t')
        print(file=hist_f)

print(now(), 'Wrote {} URLs from {} clusters'.format(n_items, len(sample)),
      file=sys.stderr)
