#!/usr/bin/env python
from __future__ import print_function
import sys
from likeable.cleaning import url_signature, strip_subdomains

for l in sys.stdin:
    l = l.rstrip('\r\n')
    sig = url_signature(l)
    print(l, '{}{}/{}'.format(*sig), strip_subdomains(sig[0]), sep='\t')
