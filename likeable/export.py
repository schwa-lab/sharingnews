from __future__ import print_function

from functools import partial
import re
from xml.sax.saxutils import escape as xml_escape

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
    return content


def _camelcase(s):
    s = unidecode(s or u'')
    return re.sub('\s', '', re.sub(r'[^\w\s]|_', '', s).title())


def build_basename(article):
    # Approximation of DailyTelegraph_150114_BenSmith_WhyThisResearchIsNewsworthy_headline
    published = article.downloaded.parse_datetime()
    return '{domain}_{date}_{author}_{headline}'.format(
        id=article.id,
        domain=article.url_signature.base_domain.replace('.', ''),
        date='-' if published is None else published.strftime('%y%m%d'),
        author=_camelcase(article.downloaded.byline) if article.downloaded.byline else '-',
        headline=_camelcase(article.downloaded.headline or article.title or 'title missing')
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
