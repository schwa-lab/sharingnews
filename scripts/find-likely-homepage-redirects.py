#!/usr/bin/env python
"""Find Articles with multiple spidered URLs, suggesting these may be homepages"""

from __future__ import print_function
import argparse
import itertools
import operator

import django
from django.db.models import Count

from likeable.models import SpideredUrl, Article

django.setup()

ap = argparse.ArgumentParser()
ap.add_argument('--by-article', action='store_true', default=False, help='By default works with distinct spidered URLs. If this flag is set, finds many articles per canonical_url.')
ap.add_argument('--since', default='2013-09-01 00:00Z')
ap.add_argument('--min-variants', type=int, default=5)
ap.add_argument('--examples-limit', type=int, default=1000, help='How many top candidates per domain should have examples found')
ap.add_argument('--num-examples', type=int, default=2, help='How many top candidates should have examples found')
args = ap.parse_args()

if not args.by_article:
    multivariant = list(SpideredUrl.objects.filter(sharewarsurl__when__gte=args.since)
                                           .values_list('article_id')
                                           .annotate(n=Count('pk'))
                                           .values_list('article__url_signature__base_domain', 'n', 'article_id', 'article__url', 'article__url_signature__signature')
                                           .filter(article__url__isnull=False, n__gte=args.min_variants)
                                           .order_by('article__url_signature__base_domain', '-n'))
else:
    multivariant = list(Article.objects.filter(spider_when__gt=args.since)
                                       .filter(downloaded__canonical_url__isnull=False, fetch_status=200)
                                       .values_list('downloaded__canonical_url')
                                       .annotate(n=Count('pk'))
                                       .filter(n__gte=args.min_variants)
                                       .order_by('downloaded__canonical_url', '-n'))
    multivariant = [(None, n, None, url, None) for url, n in multivariant]

print('URL', 'freq', 'domain', 'n_domain', 'Signature', '#slashes', 'has query',
      *['example {}'.format(i + 1) for i in range(args.num_examples)], sep='\t')
for domain, tups in itertools.groupby(multivariant, key=operator.itemgetter(0)):
    tups = list(tups)
    n_domain = len(tups)
    # include domain quantity for further filtering
    for i, tup in enumerate(tups):
        domain, n, article_id, url, sig = tup
        n_slashes = url.partition('?')[0].rstrip('/').count('/')
        has_query = '?' in url.rstrip('?')
        if args.by_article:
            examples = Article.objects.filter(downloaded__canonical_url=url)[:args.num_examples].values_list('url', flat=True) if i < args.examples_limit else ()
        else:
            examples = SpideredUrl.objects.filter(article__id=article_id)[:args.num_examples].values_list('url', flat=True) if i < args.examples_limit else ()
        print(url, n, domain, n_domain, sig, n_slashes, has_query, *examples, sep='\t')
