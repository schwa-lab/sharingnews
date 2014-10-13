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
        sig.set_selector(f, sel)
    sig.modified_when = utcnow()
    sig.save()
