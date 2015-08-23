#!/usr/bin/env python

import sys
import argparse
import itertools
import csv

from unidecode import unidecode  # may be too aggressive; can use unicodedata.normalise('NFKD'
import django

from likeable.models import Article

django.setup()

ap = argparse.ArgumentParser()
ap.add_argument('--id-file', default=sys.stdin, type=argparse.FileType('r'))
ap.add_argument('--ascii', action='store_true', default=False)
ap.add_argument('fields', nargs='+')
args = ap.parse_args()

if args.ascii:
    encode = unidecode
else:
    def encode(s):
        return s.encode('utf-8')

def batched_lines(f, n):
    batch = list(itertools.islice(f, n))
    while batch:
        yield batch
        batch = list(itertools.islice(f, n))

id_field = args.fields.index('id')

writer = csv.writer(sys.stdout)
writer.writerow(args.fields)
for id_batch in batched_lines(args.id_file, 100):
    ids = map(int, id_batch)
    tuples = Article.objects.filter(id__in=ids).bin_shares(shares_field='fb_count_5d', field_name='fb_binned_5d').values_list(*args.fields)
    tuples = sorted(tuples, key=lambda x: ids.index(x[id_field]))
    # Py2 CSV sucks:
    tuples = [[encode(x) if isinstance(x, unicode) else x for x in tup] for tup in tuples]
    writer.writerows(tuples)
