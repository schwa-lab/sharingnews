#!/usr/bin/env python
import sys
import csv

import django

from likeable.models import UrlSignature, DownloadedArticle, utcnow

django.setup()

FIELDS = DownloadedArticle.EXTRACTED_FIELDS


for entry in csv.DictReader(sys.stdin, dialect='excel-tab'):
    sig_text = entry['signature']
    if not sig_text or sig_text == '/':
        continue
    print(sig_text)
    sig = UrlSignature.objects.get(signature=sig_text)
    for f in FIELDS:
        sel = entry.get(f) or None
        setattr(sig, f + '_selector', sel)
        if sel is None:
            continue
        # validate:
        assert getattr(sig, f + '_xpath') is not None
    sig.modified_when = utcnow()
    sig.save()
