#!/usr/bin/env python
from __future__ import print_function
import sys

import django
from django.db.models import Q

from likeable.models import Article
django.setup()

limit = int(sys.argv[1])
ids = (Article.objects
             .filter(Q(fetch_status__isnull=True)|~(Q(fetch_status__in=[200, 204, 400, 401, 402, 403, 404, 410, 500]) | Q(fetch_status__lt=0)))
             .extra(select={'weight': 'random() * (log(coalesce(fb_count_5d, 0) + 3 * coalesce(tw_count_5d, 0) + 1)+ log(extract(days from fb_created - \'2007-06-01\'::timestamp)) / 4)'},
                    order_by=['-weight'])
             .values_list('id', flat=True)[:limit])
print("\n".join(map(str, ids)))
