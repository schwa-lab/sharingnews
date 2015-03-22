from __future__ import print_function, division
import csv
import sys
import argparse

import django

from likeable.models import Article

django.setup()

ap = argparse.ArgumentParser()
ap.add_argument('--field', default='fb_count_5d')
ap.add_argument('--min-count', type=int, default=3, help='Calculate trimmed quantiles instead')
ap.add_argument('--since', default='2014-01-01 00:00Z')
ap.add_argument('--until', default='2014-07-01 00:00Z')
ap.add_argument('--percentiles', default=[10, 25, 50, 75, 90], type=lambda s: [int(x) for x in s.split(',')])
args = ap.parse_args()
articles = Article.objects.filter(fetch_status=200, spider_when__gte=args.since, spider_when__lt=args.until)
articles = articles.filter(**{args.field + '__isnull': False, args.field + '__gte': args.min_count})
percentiles = args.percentiles

out = csv.writer(sys.stdout)
out.writerow(['domain', 'frequency'] + ['{}%'.format(p) for p in percentiles])
for domain in sys.stdin:
    domain = domain.strip()
    dom_articles = articles
    if domain:
        dom_articles = articles.filter(url_signature__base_domain=domain)
    try:
        N, quantiles = dom_articles.calc_share_quantiles(percentiles, 'fb_count_5d', return_count=True)
        out.writerow([domain, N] + list(quantiles))
    except Exception as e:
        print('Failure on', domain, repr(e), file=sys.stderr)
        continue
