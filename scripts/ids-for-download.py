#!/usr/bin/env python
from __future__ import print_function
import sys

import django
from django.db.models import Q

from likeable.models import Article
django.setup()

limit = int(sys.argv[1])
ids = Article.objects\
             .filter(Q(fetch_status__isnull=True)|~Q(fetch_status__in=[200, 401, 402, 403, 404, 410]))\
             .extra(select={'weight': 'random() * (log(total_shares + 1)+ log(extract(days from fb_created - \'2007-06-01\'::timestamp)) / 4)'},
                    order_by=['-weight'])\
             .values_list('id', flat=True)[:limit]
print("\n".join(map(str, ids)))
