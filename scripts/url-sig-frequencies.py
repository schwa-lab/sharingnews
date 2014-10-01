from __future__ import print_function
import sys
from collections import Counter
from likeable.cleaning import url_signature

counter = Counter()
for l in sys.stdin:
    if '|http' not in l:
        continue
    url_id, dt, url = l.strip().split('|')
    counter[dt[:7], url_signature(url)] += 1

for (mo, sig), n in counter.iteritems():
    print(n, mo, '{}{}?{}'.format(*sig), sep='\t')
