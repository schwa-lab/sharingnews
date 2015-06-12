#!/usr/bin/env python
from __future__ import print_function
import argparse
import urlparse
import re
import sys
import random
import time
import json
import csv

import requests
from lxml import html
import django

from likeable.models import Article
from likeable.countapis import FBBatchFetcher

django.setup()

def qformat(fmt):
    def apply(s):
        return fmt.format(s.replace('"', '\\"'))
    return apply


def from_url(url):
    parsed = html.fromstring(requests.get(url).text)
    search_url = parsed.get_element_by_id('wellQuery').text
    fq = urlparse.parse_qs(urlparse.urlparse(search_url).query)['fq'][0]
    expr = fq.partition(' AND ')[0]
    tmp = re.sub('".*?(?<!")"', "", expr)
    assert tmp.count('(') == tmp.count(')')
    print('Retrieved expression from {!r}: {!r}'.format(url, expr), file=sys.stderr)
    return expr


class Op(object):
    def __init__(self, op):
        self.op = op

    def __call__(self, stack, queue):
        stack.append('({} {} {})'.format(stack.pop(), self.op, next(queue)))


OR = Op('OR')
AND = Op('AND')


ap = argparse.ArgumentParser()
ap.add_argument('--loc', type=qformat('(glocations.contans:"{0}" OR glocations.contans:"\\({0}\\)")'), action='append', dest='fqueries')
ap.add_argument('--org', type=qformat('organizations:"{0}"'), action='append', dest='fqueries')
ap.add_argument('--subj', type=qformat('subject:"{0}"'), action='append', dest='fqueries')
ap.add_argument('--per', type=qformat('persons:"{0}"'), action='append', dest='fqueries')
ap.add_argument('--url', type=from_url, action='append', dest='fqueries')
ap.add_argument('-o', '--or', const=OR, action='append_const', dest='fqueries')
ap.add_argument('-a', '--and', const=AND, action='append_const', dest='fqueries')
ap.add_argument('--since', default=None, help='e.g. 2015-01-21; inclusive')
ap.add_argument('--until', default=None, help='exclusive')
ap.add_argument('--csv', action='store_true', default=False)
ap.add_argument('--db-ids-only', action='store_true', default=False,
                help='Don\'t get IDs for unfamiliar URLs from Facebook API')
ap.add_argument('text_queries', nargs='*')  # warning: no escaping added
args = ap.parse_args()

fqueries = []

if args.since is not None or args.until is not None:
    since = args.since + 'T00:00:00Z' if args.since is not None else '*'
    until = args.until + 'T00:00:00Z' if args.until is not None else '*'
    fqueries.append('pub_date:[%s TO %s}' % (since, until))

expr_iter = iter(args.fqueries)
while True:
    try:
        expr = next(expr_iter)
    except StopIteration:
        break
    if callable(expr):
        expr(fqueries, expr_iter)
    else:
        fqueries.append(expr)

# Default filters from NYTimes
fqueries.append('-type_of_material:"Editorial" AND  -type_of_material:"Correction" AND  -type_of_material:"Obituary" AND  -type_of_material:"paid death notice" AND  -headline:"paid notice" AND  -type_of_material:"Caption" AND  -type_of_material:"Summary" AND  -type_of_material:"Schedule" AND  -type_of_material:"Letter" AND  -news_desk:"Travel" AND  -news_desk:"Escapes" AND  -news_desk:"Dining" AND  -news_desk:"Fashion" AND  -news_desk:"Fashions" AND  -news_desk:"Style" AND  -news_desk:"Styles" AND  -news_desk:"Society" AND  -news_desk:"Home" AND  -news_desk:"Home/Style" AND  -news_desk:"Living" AND  -news_desk:"Beauty" AND  -news_desk:"Design" AND  -news_desk:"Theater" AND  -subject:"Theater" AND  -news_desk:"Movies" AND  -subject:"Motion Pictures" AND  -subject:"Movies" AND  -news_desk:"Great Homes and Destinations" AND -news_desk:"Opinion" AND -news_desk:"Editorials and op-ed" AND -news_desk:"Editorial Desk" AND -type_of_material:"Editorial" AND -type_of_material:"Op-Ed" AND -kicker:"Opinionator" AND -kicker:"Frank Bruni" AND -kicker:"David Brooks" AND -kicker:"Ross Douthat" AND -kicker:"Bill Keller" AND -kicker:"Nicholas D. Kristof" AND -kicker:"Paul Krugman" AND -kicker:"Joe Nocera" AND -kicker:"Loyal Opposition" AND -kicker:"The Conversation" AND -kicker:"Room for Debate" AND -headline:"Public Editor" AND  -kicker:"Public Editor"')

fq = ' AND '.join(fqueries)
q = ' '.join(args.text_queries)


docs = []
PER_PAGE = 10  # fixed, server-side
page = 0
n_pages = None
while n_pages is None or page < n_pages:
    # XXX: could use until instead of page for more precision
    params = {'fq': fq, 'q': q, 'limit': 10, 'page': page, 'type': 'article,blogpost'}
    time.sleep(random.random())
    print(params)
    resp = requests.get('http://topics.nytimes.com/svc/timestopic/v1/topic.json', params=params).json()['response']
    if n_pages is None:
        hits = resp['meta']['hits']
        print('Found {} hits for fq={!r} and q={!r}'.format(hits, fq, q))
        if hits > PER_PAGE:
            assert len(resp['docs']) == PER_PAGE
        n_pages = (hits + PER_PAGE - 1) // PER_PAGE
    docs.extend(resp['docs'])
    page += 1

def urls_to_fb_ids(urls, db_only=False):
    # TODO: move to models
    url_id_map = {url: None for url in urls}

    url_id_map.update(Article.objects.filter(url__in=url_id_map.keys()).values_list('url', 'id'))

    rem_urls = {url for url, fbid in url_id_map.items() if fbid is None}
    url_id_map.update(Article.objects.filter(spideredurl__url__in=rem_urls).values_list('spideredurl__url', 'id'))

    rem_urls = {url for url, fbid in url_id_map.items() if fbid is None}
    url_id_map.update(Article.objects.filter(downloaded__canonical_url__in=rem_urls).values_list('downloaded__canonical_url', 'id'))

    if not db_only:
        rem_urls = {url for url, fbid in url_id_map.items() if fbid is None}
        fb_results = json.loads(FBBatchFetcher('og_object{id}').fetch_auto(rem_urls))
        url_id_map.update((k, v['og_object']['id'])
                          for k, v in fb_results.items())

    return url_id_map


url_id_map = urls_to_fb_ids([doc['web_url'] for doc in docs], db_only=args.db_ids_only)
for doc in docs:
    doc['fb_id'] = url_id_map.get(doc['web_url'], None)

if args.csv:
    fields = ['web_url', 'fb_id', 'pub_date']
    writer = csv.DictWriter(sys.stdout, fieldnames=fields, extrasaction='ignore')
    writer.writeheader()
    writer.writerows(docs)
else:
    print(json.dumps(docs))
