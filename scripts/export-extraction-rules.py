#!/usr/bin/env python
# Only deals with domain defaults and global default

from __future__ import print_function
import sys

import django

from likeable.models import UrlSignature, EXTRACTED_FIELDS
from likeable.export import build_zip

django.setup()

def generate_files():
    for sig in UrlSignature.objects.all().domain_defaults():
        for field in EXTRACTED_FIELDS:
            sel = sig.get_selector(field)
            if sel.startswith('<'):
                continue
            path = '{}/{}.txt'.format(field, sig.signature)
            yield path, sel
    for field, sel in UrlSignature.DEFAULT_SELECTORS.items():
        if field in EXTRACTED_FIELDS:
            yield '{}/DEFAULT.txt'.format(field), sel


print('Writing zip file to stdout', file=sys.stderr)
build_zip(sys.stdout, generate_files())
