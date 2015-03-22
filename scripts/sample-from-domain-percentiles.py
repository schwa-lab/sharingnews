#!/usr/bin/env python
from __future__ import print_function, division
import argparse
import sys

import django
from django.db.models import Q
import numpy as np
import pandas

from likeable.models import Article

django.setup()

ap = argparse.ArgumentParser()
ap.add_argument('--quantiles-file', default=sys.stdin, type=argparse.FileType('r'))
ap.add_argument('-n', '--num-samples', default=100, type=int)
ap.add_argument('--lo', default=3, help='Value or x%%')
ap.add_argument('--hi', default=None, help='Value or x%%')
ap.add_argument('--field', default='fb_count_5d')
ap.add_argument('--since', default='2014-01-01 00:00Z')
ap.add_argument('--until', default='2014-07-01 00:00Z')
args = ap.parse_args()

articles = Article.objects.filter(fetch_status=200, spider_when__gte=args.since, spider_when__lt=args.until)
df = pandas.read_csv(args.quantiles_file)
df = df[df['domain'] > '']  # ignore overall row
#df['sample_size'] = np.random.RandomState(0).multinomial(args.num_samples, df['frequency'] / df['frequency'].sum())

if isinstance(args.lo, str) and args.lo.endswith('%'):
    df['lo'] = df[args.lo]
elif isinstance(args.lo, (str, int, float)):
    df['lo'] = np.zeros(len(df)) + int(args.lo)
else:
    assert args.lo is None


if isinstance(args.hi, str) and args.hi.endswith('%'):
    df['hi'] = df[args.hi]
elif isinstance(args.hi, (str, int, float)):
    df['hi'] = np.zeros(len(df)) + int(args.hi)
else:
    assert args.hi is None


disjunction = Q()
for idx, row in df.iterrows():
    domain_q = Q(url_signature__base_domain=row['domain'])
    if 'hi' in df:
        domain_q &= Q(**{args.field + '__lt': row['hi']})
    if 'lo' in df:
        domain_q &= Q(**{args.field + '__gte': row['lo']})
    disjunction |= domain_q

articles = articles.filter(disjunction).order_by('rand')
for article_id in articles.values_list('id', flat=True)[:args.num_samples]:
    print(article_id)

"""
for idx, row in df.iterrows():
    print('Getting', row['sample_size'], 'for', row['domain'])
    domain_articles = articles.filter(url_signature__base_domain=row['domain'])
    lims = (('__gte', args.lo), ('__lt', args.hi))
    for suf, lim in lims:
        if lim is None:
            continue
        elif isinstance(lim, (int, float)):
            pass
        elif lim.endswith('%'):
            lim = row[lim]
        else:
            lim = int(lim)
        domain_articles = domain_articles.filter(**{args.field + suf: lim})

    n = row['sample_size']
    domain_ids = list(domain_articles.values_list('id', flat=True).order_by('?')[:n])
    if len(domain_ids) != n:
        print('WARNING: Did not fill quota for', row['domain'], 'getting', len(domain_ids), 'of', n, file=sys.stderr)
    elif n == 0:
        print('WARNING: Empty quota for', row['domain'], file=sys.stderr)
    for article_id in domain_ids:
        print(article_id)
"""
