#!/usr/bin/env python

from __future__ import print_function

import sys

import django
from django.db.models import Q, F

from likeable.models import DownloadedArticle

try:
    limit = sys.argv[1]
except IndexError:
    limit = None

django.setup()
q = Q(scrape_when__isnull=True) | Q(scrape_when__lt=F('article__url_signature__modified_when'))
print(*DownloadedArticle.objects.filter(q).order_by('-in_dev_sample', 'article__url_signature__modified_when').values_list('article_id', flat=True)[:limit], sep='\n')

