#!/usr/bin/env python
from __future__ import print_function

from collections import Counter

import django
django.setup()

from likeable.models import UrlSignature

print('NB: this does not run the enqueue cron or workers')

updated = Counter()
for sig in UrlSignature.objects.all().order_by('?'):
    updated.update(sig.update_defaults())
    sig.save()

print('Updated')
for k, v in updated.items():
    print(k, v, sep='\t')
