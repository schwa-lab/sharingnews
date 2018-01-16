#!/usr/bin/env python
# removes downloaded records, resulting in re-download unless fetch_status is set

import argparse

import django

from likeable.models import DownloadedArticle

django.setup()

ap = argparse.ArgumentParser()
ap.add_argument('domains', nargs='+')
ap.add_argument('-g', '--structure-group', type=int)
ap.add_argument('-s', '--set-fetch-status', type=int, default=None)
args = ap.parse_args()

if raw_input('Are you sure (y to continue)?').strip() != 'y':
    ap.error('Cancelled')

das = DownloadedArticle.objects.filter(article__url_signature__base_domain__in=args.domains)
if getattr(args, 'structure_group', None) is not None:
    if len(args.domains) > 1:
        ap.error('At most single domain if --structure-group provided')
    das = das.filter(structure_group=args.structure_group)

das.delete(fetch_status=args.set_fetch_status)
