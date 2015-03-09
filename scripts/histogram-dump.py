#!/usr/bin/env python
from __future__ import print_function, division
import sys
import csv

import django
from django.db.models import Count

from likeable.models import FINE_HISTOGRAM_BINS, Article

def bin_edges(i):
    if i == 0:
        lo = -1
    else:
        lo = FINE_HISTOGRAM_BINS[i - 1]
    return lo, FINE_HISTOGRAM_BINS[i]

django.setup()


articles = Article.objects.filter(fetch_status=200).filter(spider_when__gte='2014-01-01 00:00Z', spider_when__lt='2014-07-01 00:00Z')
articles = articles.filter(fb_count_5d__isnull=False, tw_count_5d__isnull=False)
articles = articles.bin_shares(FINE_HISTOGRAM_BINS, 'fb_binned', 'fb_count_5d').bin_shares(FINE_HISTOGRAM_BINS, 'tw_binned', 'tw_count_5d')
hist = articles.values_list('url_signature__base_domain', 'fb_binned', 'tw_binned').annotate(n=Count('pk'))

def group_to_min_shares(grp):
    return 'CASE WHEN ({0}) = 0 THEN 0 ELSE ceil(power(10, (({0}) - 1) / 10.)) END'.format(grp)

###hist = hist.extra(select={'min_tw': group_to_min_shares('tw_binned'),
###                          'max_tw': group_to_min_shares('tw_binned + 1') + '-1',
###                          'min_fb': group_to_min_shares('fb_binned'),
###                          'max_fb': group_to_min_shares('fb_binned + 1') + '-1',
###                          'example': '(select title || \' | \' || url from likeable_article where fb_count_5d >= min_fb and fb_count_5d <= max_fb and tw_count_5d >= min_tw and tw_count_5d <= max_tw limit 1)'})\
###           .values_list('url_signature__base_domain', 'fb_binned', 'tw_binned', 'n', 'min_fb', 'max_fb', 'min_tw', 'max_tw', 'example')

writer = csv.writer(sys.stdout)
writer.writerow(('domain', 'fb@5d group', 'tw@5d group', 'frequency', 'example title', 'example url'))
###writer.writerow(('domain', 'fb@5d group', 'tw@5d group', 'frequency', 'min fb', 'max fb', 'min tw', 'max tw', 'example'))
for row in hist:
    # slow:
    min_fb, max_fb = bin_edges(row[1])
    min_tw, max_tw = bin_edges(row[2])
    example = Article.objects.filter(url_signature__base_domain=row[0], fb_count_5d__gt=min_fb, fb_count_5d__lte=max_fb, tw_count_5d__gt=min_tw, tw_count_5d__lte=max_tw).order_by('?').first()
    writer.writerow(row + (example.title.encode('utf8'), example.url.encode('utf8')))

# Fast way to get example per group is to populate table foo with boundaries and
# explain select (select url from likeable_article where fb_count_longterm >= min_shares and fb_count_longterm < max_shares limit 1), min_shares, max_shares from foo;
# However may require index, and no randomness
