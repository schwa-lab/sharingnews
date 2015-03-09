#!/usr/bin/env python
import sys

import django
from dateutil.tz import tzutc
import datetime
import re

from likeable.models import Site

django.setup()
UTC = tzutc()


def _parse_iso8601(s):  # parses as UTC
    if not s:
        return
    return datetime.datetime(*map(int, re.split('[^\d]', s)[:-1]), tzinfo=UTC)


def parse_bool(b):
    b = b.lower()
    if b.startswith('t'):
        return True
    if b.startswith('f'):
        return False
    if not b:
        # return None
        return False
    return int(b)


header = next(sys.stdin).rstrip().split('|')
for l in sys.stdin:
    row = dict(zip(header, l.rstrip().split('|')))
    values = {
        'name': row['site_Name'],
        'url': row['site_Url'],
        'url': row['site_Url'],
        'rss_url': row['site_RssUrl'],
        'last_fetch': _parse_iso8601(row['site_lastFetch']),
        'health_start': _parse_iso8601(row['site_healthStart']),
        'is_healthy': parse_bool(row['site_isHealthy']),
        'active': parse_bool(row['site_active']),
    }
    if values['url'] == values['rss_url']:
        del values['rss_url']
    site, created = Site.objects.get_or_create(id=int(row['site_Id']),
                                               defaults=values)
    if not created:
        for k, v in values.items():
            setattr(site, k, v)
        site.save()
