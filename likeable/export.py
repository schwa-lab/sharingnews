from __future__ import print_function

from functools import partial
import re
import csv
import io
import itertools
import zipfile
from xml.sax.saxutils import escape as xml_escape
from collections import Counter

from unidecode import unidecode  # may be too aggressive; can use unicodedata.normalise('NFKD'

from likeable.cleaning import insert_base_href


def format_url(article):
    return u'[InternetShortcut]\nURL={}'.format(article.url)


def format_redirect_page(article):
    return '''
           <html>
           <head><meta http-equiv="refresh" content="0; url={0}"></head>
           <body><p>Redirecting to <a href="{0}">{0}</a></p></body>
           </html>
           '''.format(xml_escape(article.url, entities={'"': '&quot;'}))


def format_html(article):
    return insert_base_href(article.downloaded.html, article.url)


def _format_text_field(article, field, ascii=True):
    content = getattr(article.downloaded, field)
    if content is None:
        return u''
    if ascii:
        try:
            content = unidecode(content).decode('ascii')
        except Exception:
            print(field, content)
            raise
    return content.replace('\n', '\r\n') + '\r\n'


def _camelcase(s, max_n_words=15):
    s = unidecode(s or u'')
    return ''.join(re.sub(r'[^\w\s]|_', '', s).title().split()[:max_n_words])


def build_basename(article):
    # Approximation of DailyTelegraph_150114_BenSmith_WhyThisResearchIsNewsworthy_headline
    published = article.downloaded.parse_datetime(warn=False) or article.spider_when
    return '{domain}_{date}_{author}_{headline}'.format(
        id=article.id,
        domain=article.url_signature.base_domain.replace('.', ''),
        date=published.strftime('%y%m%d'),
        author=_camelcase(article.downloaded.byline) if article.downloaded.byline else u'-',
        headline=_camelcase(article.downloaded.headline or article.title or u'title missing')
    )


def export_folders(article, basename=None, ascii=True):
    """Generates (path, io.StringIO) tuples
    """
    if basename is None:
        basename = build_basename(article)

    ext = '.ascii.txt' if ascii else '.txt'  # NOQA
    format_field = partial(_format_text_field, article, ascii=ascii)
    fmt = lambda s: s.format(ext=ext, basename=basename)

    yield fmt('web/{basename}.redirect.html'), format_redirect_page(article)
    yield fmt('html/{basename}.html'), format_html(article)
    yield fmt('fulltext/{basename}.fulltext{ext}'), format_field('full_text')
    yield fmt('headline/{basename}.headline{ext}'), format_field('headline')
    yield fmt('lead/{basename}.lead{ext}'), format_field('first_paragraph')
    yield fmt('body/{basename}.body{ext}'), format_field('body_text')


def gen_export_folders(groups, articles, BATCH_SIZE=200, measure_names=['share_measure'], group_dirs=None):
    """

    - groups is a list of lists of (article id, *measures)
    - articles is a queryset

    """
    seen_names = Counter()
    index_file = io.BytesIO()
    index_writer = csv.writer(index_file)
    index_writer.writerow(['group'] + list(measure_names) + ['filename', 'id', 'url', 'pubdate', 'body_wordcount'])
    group_digits = len(str(len(groups)))
    for i, group in enumerate(groups):
        if group_dirs is None:
            group_dir = 'group{:0{n}d}/'.format(i + 1, n=group_digits)
        else:
            group_dir = group_dirs[i] + '/'
        group_num = str(i + 1)
        group = iter(group)
        while True:
            batch = itertools.islice(group, BATCH_SIZE)
            batch = list(batch)
            if not batch:
                break

            lookup = articles.in_bulk([row[0] for row in batch])
            for row in batch:
                article = lookup[row[0]]
                if article.fetch_status != 200:
                    # HACK!
                    import sys
                    print(article.id, article.fetch_status, file=sys.stderr)
                    index_writer.writerow([group_num,] + list(row[1:]) + ['<JUNK: status %d>' % article.fetch_status,
                                           article.id, article.url,
                                           '', ''])
                    continue
                basename = build_basename(article)
                seen_names[basename] += 1
                if seen_names[basename] > 1:
                    print('Duplicate basename for %d: %s' % (article.id, basename), file=sys.stderr)
                    basename += '_(%d)' % seen_names[basename]
                if article.downloaded.body_text is None:
                    word_count = 0
                else:
                    word_count = len(article.downloaded.body_text.split())
                try:
                    pubdate = article.downloaded.parse_datetime(warn=False).isoformat()
                except Exception:  # XXX should be more specific
                    pubdate = ''
                if not pubdate:
                    pubdate = article.spider_when
                index_writer.writerow([group_num,] + list(row[1:]) + [basename.encode('utf8'),
                                       article.id, article.url,
                                       pubdate,
                                       word_count])
                for filename, content in export_folders(article, basename=basename, ascii=True):
                    yield group_dir + filename, content

        index_file.seek(0)
        yield 'index.csv', index_file


def build_zip(fout, files):
    archive = zipfile.ZipFile(fout, 'w', zipfile.ZIP_DEFLATED)
    for filename, content in files:
        if hasattr(content, 'read'):
            content = content.read()
        elif not isinstance(content, str):
            content = content.encode('utf8')
        archive.writestr(filename, content)
    archive.close()
