from __future__ import print_function
import zipfile
import itertools
import csv
import StringIO

import django
django.setup()

from likeable.models import Article, UrlSignature
from likeable.archive import get_archive_json
from likeable.export import build_basename

all_domains = sorted(UrlSignature.objects.values_list('base_domain', flat=True).distinct())

OUT = '/n/schwa07/data1/joel/sharingnews-dump-201801/archive-json/'


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
        path = OUT + tup_str + '.zip'
        print(path)
        with zipfile.ZipFile(path, 'w') as zf:
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
                zf.writestr(filename, get_archive_json(art) + '\n')
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
