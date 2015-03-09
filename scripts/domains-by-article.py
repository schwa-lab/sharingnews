#!/usr/bin/env python
from __future__ import print_function, division
import django
from django.db.models import Count

from likeable.models import Article

django.setup()
for row in Article.objects.values('url_signature__base_domain').annotate(n=Count('pk')).order_by('-n').values_list('url_signature__base_domain', 'n'):
    print(*row, sep='\t')
