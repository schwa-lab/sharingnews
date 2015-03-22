#!/usr/bin/env python
# for each domain identify which structure groups are well represented

from __future__ import print_function, division
import argparse
import sys
from collections import defaultdict
import math

import django
from django.db.models import Count

from likeable.models import DownloadedArticle

django.setup()

ap = argparse.ArgumentParser()
ap.add_argument('--min-per-structure', type=int, default=2)
ap.add_argument('--max-per-domain', type=int, default=200)
ap.add_argument('--max-per-structure', type=int, default=40)
ap.add_argument('--domain-file', type=argparse.FileType('r'), default=sys.stdin)
ap.add_argument('--dry-run', default=False, action='store_true')
args = ap.parse_args()


print('domain', 'group', 'total', 'former', 'proposed', sep='\t')
for domain in sys.stdin:
    domain = domain.strip()
    print(domain, file=sys.stderr)
    freqs = list(DownloadedArticle.objects.filter(article__url_signature__base_domain=domain).values_list('structure_group', 'in_dev_sample').annotate(n=Count('pk')))
    former_freq_dist = {group: n for group, in_dev_sample, n in freqs if in_dev_sample}
    total_freq_dist = defaultdict(int)
    for group, _, n in freqs:
        total_freq_dist[group] += n
    target_freq_dist = {group: args.min_per_structure for group in total_freq_dist}
    n_remaining = args.max_per_domain - sum(target_freq_dist.values())
    squashed_freq_dist = {group: math.sqrt(n) for group, n in total_freq_dist.items()}
    rate = n_remaining / sum(squashed_freq_dist.values())
    for group, n in squashed_freq_dist.items():
        target_freq_dist[group] += int(n * rate)
        target_freq_dist[group] = min(target_freq_dist[group], args.max_per_structure)
        print(domain, group, total_freq_dist[group], former_freq_dist.get(group, 0), target_freq_dist[group], sep='\t')

    if not args.dry_run:
        DownloadedArticle.objects.filter(article__url_signature__base_domain=domain, in_dev_sample=True).update(in_dev_sample=False)
        ids = []
        for group, n in target_freq_dist.items():
            addition = list(DownloadedArticle.objects.filter(article__url_signature__base_domain=domain, structure_group=group).order_by('?').values_list('article_id', flat=True)[:n])
            if len(addition) != n:
                print('Wanted', n, 'got', len(addition), 'for', domain, 'group', group)
            ids.extend(addition)
        DownloadedArticle.objects.filter(article_id__in=ids).update(in_dev_sample=True)
        print('saved for', domain, file=sys.stderr)
