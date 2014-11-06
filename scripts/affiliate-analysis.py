#!/usr/bin/env python
"""Gathers count data for URLs found in parallel domains
"""

from __future__ import print_function, absolute_import
import time
import argparse
import sys
import json
import os

import django
django.setup()

from likeable.models import Article
from likeable.countapis import fetch_twitter, fetch_facebook_rest, fetch_facebook_ids, retry_until_success


fetch_twitter = retry_until_success(fetch_twitter)
fetch_facebook_rest = retry_until_success(fetch_facebook_rest)
fetch_facebook_ids = retry_until_success(fetch_facebook_ids)


def fetch_data(entries, domains):
    for i, entry in enumerate(entries):
        entry['rank'] = i + 1
        fburls = []
        if 'twitter' not in entry:
            entry['twitter'] = {}
        if 'fbdata' not in entry:
            entry['fbdata'] = {}
            entry['fbgraph'] = {}
        for domain in domains:
            url = 'http://{}/{}'.format(domain, entry['url'].split('/', 3)[-1])
            if domain not in entry['fbgraph'] or 'og_object' not in entry['fbgraph'][domain]:
                fburls.append(url)
            if domain in entry:
                entry['twitter'][domain] = entry.pop(domain)
            if domain in entry['twitter']: continue
            entry['twitter'][domain] = fetch_twitter(url).json()['count']
            time.sleep(0.2)
        if fburls:
            fbdata = fetch_facebook_rest(fburls).json()
            entry['fbdata'].update({fbe['url'].split('/')[2]: fbe for fbe in fbdata})
            time.sleep(0.2)
            fbgraph = fetch_facebook_ids(fburls).json()
            entry['fbgraph'].update({k.split('/')[2]: fbe for k, fbe in fbgraph.items()})
            time.sleep(0.2)
        print('>', i, entry['url'], entry['total_shares'], file=sys.stderr)


def print_raw(entries, domains, f):
    print('path', 'domain', 'src=tgt', 'tgt', 'twitter', 'FBGtotal', 'FBRtotal', 'FBRshare', 'FBRlike', 'FBRcomment', 'FBRcommentsbox', 'FBRclick', sep='\t', file=f)
    for entry in entries:
        for domain in domains:
            print(entry['url'].split('/', 3)[-1], domain, entry['fbgraph'][domain]['og_object']['url'] == entry['fbgraph'][domain]['id'], entry['fbgraph'][domain]['og_object']['url'].split('/')[2], entry['twitter'][domain], entry['fbgraph'][domain]['share']['share_count'], '{0[total_count]}\t{0[share_count]}\t{0[like_count]}\t{0[comment_count]}\t{0[commentsbox_count]}\t{0[click_count]}'.format(entry['fbdata'][domain]), sep='\t', file=f)


def print_summary(entries, domains, f):
    print('path', *['Tw {0}\tFB {0}'.format(domain) for domain in domains], sep='\t', file=f)
    for entry in entries:
        row = [entry['url'].split('/', 3)[-1]]
        for domain in domains:
            row.append(entry['twitter'][domain])
            #if entry['fbgraph'][domain]['og_object']['url'] == entry['fbgraph'][domain]['id']:
            if '://{}/'.format(domain) in entry['fbgraph'][domain]['og_object']['url']:
                row.append(entry['fbgraph'][domain]['share']['share_count'])
            else:
                row.append('')
        print(*row, sep='\t', file=f)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('base_domain')
    ap.add_argument('domains', help='comma-delimited substitute domains')
    ap.add_argument('out_prefix')
    ap.add_argument('--url-startswith')
    ap.add_argument('--url-endswith')
    ap.add_argument('-n', '--count', required=True)
    ap.add_argument('-u', '--update', help='path to JSON to load as partial results')
    args = ap.parse_args()

    domains = [domain.strip() for domain in args.domains.split(',')]

    open(args.out_prefix + '.summary.txt', 'w').close()
    print('Listing URLs', file=sys.stderr)
    articles = Article.objects.filter(url_signature__base_domain=args.base_domain)
    if getattr(args, 'url_startswith', None):
        articles = articles.filter(url__startswith=args.url_startswith)
    if getattr(args, 'url_endswith', None):
        articles = articles.filter(url__endswith=args.url_endswith)
    articles = articles.order_by('-total_shares')
    if articles.count() == 0:
        ap.error('No articles found')
    entries = list(articles.values('url', 'total_shares')[:args.count])

    if getattr(args, 'update', None):
        old_entries = {entry['url']: entry for entry in json.load(open(args.update))}
        print('Read', len(old_entries), 'former entries', file=sys.stderr)
        for entry in entries:
            entry.update(old_entries.get(entry['url'], {}))

    print('Fetching count data', file=sys.stderr)
    try:
        fetch_data(entries, domains)
    except Exception:
        print('Exception thrown, saving to %s.json' % args.out_prefix, file=sys.stderr)
        with open(args.out_prefix + '.json', 'wb') as fout:
            json.dump(entries, fout)
        raise
    print('Saving to %s.{json,raw.txt,summary.txt}' % args.out_prefix, file=sys.stderr)
    with open(args.out_prefix + '.json', 'wb') as fout:
        json.dump(entries, fout)
    with open(args.out_prefix + '.raw.txt', 'wb') as fout:
        print_raw(entries, domains, fout)
    with open(args.out_prefix + '.summary.txt', 'wb') as fout:
        print_summary(entries, domains, fout)


if __name__ == '__main__':
    main()
