from __future__ import print_function
import os
import zipfile
import itertools
import csv
import StringIO
import argparse

import django
django.setup()

from likeable.models import Article, UrlSignature
from likeable.archive import get_archive_json
from likeable.export import build_basename


def _exclude_type(s):
    return [x.split('.') for x in s.split(',')]
ap = argparse.ArgumentParser()
ap.add_argument('out_dir')
ap.add_argument('--exclude', type=_exclude_type,
                default=_exclude_type('facebook_metadata.description,count.binned_facebook_shares,count.binned_twitter_shares,fetch.html,fetch.user_agent_spoof,scrape,extract.lead'),
                help='Comma-delimited list of json paths to exclude from export')
args = ap.parse_args()

all_domains = sorted(UrlSignature.objects.values_list('base_domain', flat=True).distinct())

def _get_spider_when(art):
    if art.spider_when is not None:
        return art.spider_when.year, art.spider_when.month
    return 0, 0


for base_domain in all_domains:
    print('===', base_domain, '===')
    articles = (Article.objects
                .filter(url_signature__base_domain=base_domain)
                .bin_all_shares()
                .select_related()
                .order_by('spider_when'))
    for (year, month), arts in itertools.groupby(articles.iterator(), _get_spider_when):
        tup_str = '{}-{:>04}-{:>02}'.format(base_domain, year, month)
        path = os.path.join(args.out_dir, tup_str + '.zip')
        print(path)
        with zipfile.ZipFile(path, 'w', allowZip64=True) as zf:
            manifest = []
            for art in arts:
                try:
                    filename = str(art.id) + '-' + build_basename(art) + '.json'
                    wc = len(art.downloaded.body_text.split())
                    hl = art.downloaded.headline or art.title
                    dl = art.downloaded.dateline
                except Exception:
                    filename = str(art.id) + '.json'
                    wc = 0
                    hl = art.title
                    dl = ''
                zf.writestr(filename, get_archive_json(art, exclude=args.exclude) + '\n')
                manifest.append({
                    'filename': filename.encode('utf8'),
                    'binned_facebook_shares_5d': art.binned_fb_count_5d,
                    'body_word_count': wc,
                })

            sio = StringIO.StringIO()
            writer = csv.DictWriter(sio,
                                    ['filename', 'binned_facebook_shares_5d',
                                     'body_word_count'])
            writer.writeheader()
            writer.writerows(manifest)
            zf.writestr('MANIFEST.csv', sio.getvalue())
