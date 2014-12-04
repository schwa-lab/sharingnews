# -*- coding: utf-8 -*-

from __future__ import print_function, absolute_import, division
import re
import logging
import datetime
import urllib
from collections import Counter, defaultdict, namedtuple

import pytz
from lxml import etree
from readability import readability
from django.db import models
from django.core.urlresolvers import reverse
from dateutil.parser import parse as parse_date

from .cleaning import xml_unescape
from .scraping import extract, DEFAULT_CODE

logger = logging.getLogger(__name__)


def utcnow():
    return datetime.datetime.utcnow().replace(tzinfo=pytz.utc)


class UrlSignatureQS(models.query.QuerySet):
    def count_field(self, field):
        return self.filter(**{field + '__isnull': False})\
                   .values_list(field)\
                   .annotate(n=models.Count('pk'))


class UrlSignatureManager(models.Manager):
    def get_queryset(self):
        return UrlSignatureQS(self.model)

    def for_base_domain(self, domain):
        return self.filter(base_domain=domain)


def _make_extractor(field):
    def _extractor(self, doc, as_unicode=False):
        return extract(self.get_selector(field), doc, as_unicode)
    _extractor.__name__ = 'extract_' + field
    return _extractor


_empty_doc = etree.fromstring('<x></x>')


EXTRACTED_FIELDS = ['headline', 'dateline', 'byline', 'body_text',]# 'body_html']

class UrlSignature(models.Model):
    objects = UrlSignatureManager()
    signature = models.CharField(max_length=256, unique=True, db_index=True)  # not sure if it's a good idea to use this as a string primary key. would make SpideredUrl big.
    base_domain = models.CharField(max_length=50, db_index=True)  # oversized due to broken data :(

    modified_when = models.DateTimeField(default=utcnow)  # selectors modified at this timestamp

    # When updating defaults, run makemigrations, and scripts/reextract-defaults.py
    DEFAULT_SELECTORS = {
        'headline': DEFAULT_CODE + '((text))[itemprop~="headline"]; ((text))h1; [property~="og:title"]::attr(content)',
        'body_text': DEFAULT_CODE + '((text))((readability.summary))p',
        # there are more variations of the following that could be generated e.g. content attr, text content (worth the cost for non-ISO?)
        'dateline': DEFAULT_CODE + '[property~=datePublished]::attr(datetime); [property~=dateCreated]::attr(datetime); [itemprop~=datePublished]::attr(datetime); [itemprop~=dateCreated]::attr(datetime)',
        #'body_html': DEFAULT_CODE + '((readability.summary))',
    }

    body_html_selector = models.CharField(max_length=1000, null=True,
                                          default=DEFAULT_SELECTORS.get('body_html'))
    body_text_selector = models.CharField(max_length=1000, null=True,
                                          default=DEFAULT_SELECTORS.get('body_text'))
    headline_selector = models.CharField(max_length=1000, null=True,
                                         default=DEFAULT_SELECTORS.get('headline'))
    dateline_selector = models.CharField(max_length=1000, null=True,
                                         default=DEFAULT_SELECTORS.get('dateline'))
    byline_selector = models.CharField(max_length=1000, null=True,
                                       default=DEFAULT_SELECTORS.get('byline'))
    media_selector = models.CharField(max_length=1000, null=True,
                                      default=DEFAULT_SELECTORS.get('media'))

    def get_selector(self, field):
        return getattr(self, field + '_selector')

    def update_defaults(self):
        updated = []
        for field in EXTRACTED_FIELDS:
            cur_sel = self.get_selector(field)
            if cur_sel is None or cur_sel.startswith(DEFAULT_CODE):
                if self.set_selector(field, self.DEFAULT_SELECTORS.get(field)):
                    updated.append(field)
        return updated

    def set_selector(self, field, value):
        if not value:
            value = None
        if value == getattr(self, field + '_selector'):
            return False

        setattr(self, field + '_selector', value)
        # smoke test
        getattr(self, 'extract_' + field)(_empty_doc)
        self.set_modified()
        return True

    def set_modified(self):
        self.modified_when = utcnow()

    # ?require match zero or one object, except media_selector
    # when changed, rerun over signature dev articles; maybe should store stats with selectors

    # Accessors for converted form
    extract_body_html = _make_extractor('body_html')
    extract_body_text = _make_extractor('body_text')
    extract_headline = _make_extractor('headline')
    extract_dateline = _make_extractor('dateline')
    extract_byline = _make_extractor('byline')
    extract_media = _make_extractor('media')

    def get_absolute_url(self):
        return reverse('likeable.views.collection',
                       kwargs={'sig': self.signature,
                               'start': '',
                               'end': ''})


class ArticleQS(models.query.QuerySet):
    def calc_share_quantiles(self, percentiles=[50, 75, 90, 95, 99]):  #  min_fb_created=None, max_fb_created=None):
        nonzero_shares = (self.filter(total_shares__gt=0)
                              .values_list('total_shares', flat=True)
                              .order_by('total_shares'))
        #N = nonzero_shares.count()
        nonzero_shares = list(nonzero_shares)
        N = len(nonzero_shares)
        return [nonzero_shares[int(N * p / 100)]
                for p in percentiles]

    def bin_shares(self, bin_max, field_name='binned_shares', shares_field='total_shares'):
        cases = ' '.join('WHEN {} <= {} THEN {}'.format(shares_field, int(m), i)
                         for i, m in enumerate(bin_max))
        return self.filter(total_shares__isnull=False).extra(select={field_name: 'CASE {} ELSE {} END'.format(cases, len(bin_max))})

    def annotate_stats(self, field='total_shares'):
        return self.annotate(count=models.Count('pk'),
                             avg=models.Avg(field),
                             min=models.Min(field),
                             max=models.Max(field))

    def domain_frequencies(self):
        return self.values_list('url_signature__base_domain').annotate(count=models.Count('pk')).order_by('-count')

    def signature_frequencies(self, return_id=False):
        field = 'url_signature__signature' if not return_id else 'url_signature'
        return self.values_list(field).annotate(count=models.Count('pk')).order_by('-count')


class ArticleManager(models.Manager):
    def get_queryset(self):
        return ArticleQS(self.model)


class Article(models.Model):
    objects = ArticleManager()

    # From Facebook's URL lookup
    id = models.BigIntegerField(null=False, primary_key=True,
                                help_text="Facebook's numeric ID")
    url_signature = models.ForeignKey(UrlSignature, null=True, db_index=True)  # null only when loading
    url = models.URLField(max_length=1000, db_index=True)  # canonical URL according to Facebook
    fb_updated = models.DateTimeField(null=True)
    fb_type = models.CharField(max_length=35, null=True)
    fb_has_title = models.BooleanField(default=False, db_index=True)  # for easy indexing
    title = models.CharField(max_length=1000, null=True)  # taken from Facebook scrape
    description = models.TextField(null=True)
    total_shares = models.PositiveIntegerField(null=True)  # tmp

    fetch_status = models.IntegerField(null=True)
    # fetch_when = models.DateTimeField(null=True)

    ### From FB id lookup
    fb_created = models.DateTimeField(null=True, db_index=True)
    # fields include: site_name, image, video, admins, application, data
    # site_name = models.CharField(max_length=30)  # or use foreignkey enum

    # image and video is a bit tricky. could store image information, but may
    # be more focused if we get it from our own scrape. video may be more selective.

    # data includes author, publisher, published_time, modified_time, and
    # section metadata, but is rarely available so should possibly be relegated
    # to a separate Model.

    # fb_author_id = models...
    # fb_author = models.TextField(null=True)

    # is_error_page = models.BooleanField(null=True)  # from extraction or inference

    ### From readability ??

    def get_absolute_url(self):
        return reverse('likeable.views.article', kwargs={'id': self.id})

    class Meta:
        index_together = [
            ('url_signature', 'fb_created'),
            ('fetch_status', 'url_signature'),
            ('total_shares', 'url_signature'),
        ]

ISO_DATE_RE = ('^[12][0-9]{3}'
               '-?[01][0-9]'
               '-?[0-3][0-9]'
               '([T ]?[0-2][0-9]'
                   '([.,][0-9]+'
                       '|:?[0-5][0-9]'
                       '([.,][0-9]+'
                           '|:?[0-5][0-9]'
                           '([.,][0-9]+)?'
                       ')?'
                   ')'
                   '(Z'
                   '|[+-][01][0-9](:?[0-5][0-9])?)?'
               ')?$')
assert re.search(ISO_DATE_RE, '2001-05-01')
assert re.search(ISO_DATE_RE, '20010501')
assert re.search(ISO_DATE_RE, '1998-05-01T19:30Z')
assert re.search(ISO_DATE_RE, '1998-05-01T19.5Z')
assert re.search(ISO_DATE_RE, '1998-05-01T19:00:45.123Z')
assert re.search(ISO_DATE_RE, '1998-05-01T1900+10')
assert re.search(ISO_DATE_RE, '1998-05-01T1900+10:30')
assert re.search(ISO_DATE_RE, '1998-05-01T1900-10:30')
assert re.search(ISO_DATE_RE, '19980501T1900Z')
assert re.search(ISO_DATE_RE, '19980501T1900')
assert re.search(ISO_DATE_RE, '199805011900Z')
# TODO: negative instances?


class DownloadedArticleQS(models.query.QuerySet):
    def add_diagnostics(self, values=False):
        select = {}
        for extra in DownloadedArticle.DIAGNOSTIC_EXTRAS:
            for field in extra.fields or DownloadedArticle.EXTRACTED_FIELDS:
                select[field + '_has_' + extra.name] = extra.expr % field
        q = self.extra(select=select)
        if values:
            keys = select.keys()
            if hasattr(values, '__iter__'):
                keys = list(keys) + list(values)
            q = q.values(*keys)
        return q


class DownloadedArticleManager(models.Manager):
    def get_queryset(self):
        return DownloadedArticleQS(self.model)

DiagnosticExtra = namedtuple('DiagnosticExtra', 'name expr fields')


class DownloadedArticle(models.Model):
    objects = DownloadedArticleManager()

    article = models.OneToOneField(Article, primary_key=True, related_name='downloaded')

    ### From our extraction
    in_dev_sample = models.BooleanField(default=False, db_index=True)
    html = models.TextField()  # fetched HTML content normed to UTF-8, with some lossy compression
    fetch_when = models.DateTimeField(null=True)
    scrape_when = models.DateTimeField(null=True)  # set to signature's modified_when, not scrape time
    canonical_url = models.TextField(null=True)

    EXTRACTED_FIELDS = EXTRACTED_FIELDS
    headline = models.TextField(null=True)
    dateline = models.TextField(null=True)
    byline = models.TextField(null=True)
    body_text = models.TextField(null=True)
    body_html = models.TextField(null=True)  # should this be stored?
    # media = models.ManyToMany(MediaItem)
    # comments_data = models.OneToOneField(CommentsData)

    @property
    def full_text(self):
        return u'{}\n\n{}'.format((self.headline or u'').strip(),
                                (self.body_text or u'').strip())

    @property
    def first_paragraph(self):
        if self.body_text is None:
            return
        return self.body_text.strip().partition(u'\n')[0]

    def parse_datetime(self):
        if self.dateline is None:
            return None
        try:
            return parse_date(self.dateline.split('yyyy-')[0])  # HACK: fix some dodgy ISO formatting
        except Exception:
            logger.warn('Failed to parse date: {!r}'.format(self.dateline))

    def _get_meta_fields(self):
        for tag in re.findall('(?i)<meta\s.*?>', self.html):
            name = re.search(r'(?i)\bname=(["\'])(.*?)\1', tag)  # TODO: support unquoted
            if name is None:
                continue
            name = name.group(2)
            content = re.search(r'(?i)\bcontent=(["\'])(.*?)\1', tag)  # TODO: support unquoted
            if content is None:
                logging.warn('Found name but no content in %s', tag)
                continue
            # todo: unescape
            yield name, xml_unescape(content.group(2))

    @property
    def meta_fields(self):
        return sorted(self._get_meta_fields())

    SEMANTIC_ANNOTATION_SCHEMES = [
        ('rdfa', 'http://www.w3.org/2012/pyRdfa/extract?uri={}&format=json&rdfagraph=output&vocab_expansion=false&rdfa_lite=false&embedded_rdf=true&space_preserve=true&vocab_cache=true&vocab_cache_report=false&vocab_cache_refresh=false', [
            ('property', etree.XPath('//*[@property]/@property')),
            ('datatype', etree.XPath('//*[@property and @datatype]/@property')),
            ('no content', etree.XPath('//*[@property and not(@content)]/@property')),
        ]),
        ('microdata', 'http://rdf.greggkellogg.net/distiller?format=jsonld&in_fmt=microdata&uri={}', [
            ('itemprop', etree.XPath('//*[@itemprop]/@itemprop')),
            ('datetime', etree.XPath('//*[@itemprop and @datetime]/@itemprop')),
        ]),
        ('hNews microformat', 'https://mf2py.herokuapp.com/parse?url={}', [
            ('hentry', etree.XPath("//*[@class and contains(concat(' ', normalize-space(@class), ' '), ' hentry ')]")),
            ('dateline', etree.XPath("//*[@class and contains(concat(' ', normalize-space(@class), ' '), ' hentry ')]/descendant-or-self::*[@class and contains(concat(' ', normalize-space(@class), ' '), ' dateline ')]")),
        ])
    ]

    def sniff_semantic_annotation(self):
        parsed = self.parsed_html
        for scheme, url_fmt, matchers in self.SEMANTIC_ANNOTATION_SCHEMES:
            results = []
            for field, matcher in matchers:
                matches = matcher(parsed)
                if matches:
                    if not hasattr(matches[0], 'tag'):
                        values = sorted(set(map(unicode, matches)))
                    else:
                        values = None
                if matches:
                    results.append((field, len(matches), values))
            url = url_fmt.replace('{}', urllib.quote(self.article.url))
            yield scheme, url, results

    @property
    def pyreadability(self):
        doc = readability.Document(self.html)
        return {'short_title': doc.short_title(),
                'summary': doc.summary()}

    @property
    def parsed_html(self):
        if not self.html:
            # XXX: Perhaps AttributeError more appropriate,
            #      but needs to apply when fromstring returns None too
            return
        # etree will not accept encoding header with unicode input:
        html = re.sub('(?i)^([^>]*) encoding=[^> ]*', r'\1', self.html)
        return etree.fromstring(html, parser=etree.HTMLParser(),
                                base_url=self.article.url)

    _fmt = '("%s" {} \'{}\')::int'.format
    DIAGNOSTIC_EXTRAS = [
        DiagnosticExtra('null', '("%s" is null)::int', None),
        DiagnosticExtra('markup', _fmt('~', '.*<.+>.*'), ('headline', 'byline', 'body_text', 'dateline')),
        DiagnosticExtra('newline', _fmt('~', r'.*\n.*'), ('headline', 'byline', 'dateline',)),
        DiagnosticExtra('emptyline', _fmt('~', r'.*\n\n.*'), None),
        DiagnosticExtra('loosepunc', _fmt('~', r'.*\s[^[:alnum:]_–—―-]\s.*'), None),
        DiagnosticExtra('noniso', _fmt('!~', ISO_DATE_RE), ('dateline',)),
    ]
    del _fmt


def dev_sample_diagnostics():
    sig_counters = defaultdict(Counter)
    sig_n_dev = Counter()

    for data in DownloadedArticle.objects.filter(in_dev_sample=True).add_diagnostics(values=['article__url_signature']):
        sig_id = data.pop('article__url_signature')
        sig_counters[sig_id].update(k for k, v in data.iteritems() if v)
        sig_n_dev[sig_id] += 1

    no_dev_sample = []
    signatures = {sig.id: sig for sig in UrlSignature.objects.filter(id__in=sig_n_dev)}
    for sig_id, count in Article.objects.all().signature_frequencies(return_id=True):
        if sig_id not in sig_counters:
            no_dev_sample.append(sig_id)
            continue
        counter = sig_counters[sig_id]
        nested = defaultdict(dict)
        for k, v in counter.iteritems():
            field, criterion = k.split('_has_')
            nested[field][criterion] = v
        yield signatures[sig_id], count, sig_n_dev[sig_id], nested


class FacebookStat(object):
    when = models.DateTimeField()
    # likes = models.PositiveIntegerField()
    # comments = models.PositiveIntegerField()
    share_total = models.PositiveIntegerField()
    page_comments = models.PositiveIntegerField(null=True)


class SpideredUrl(models.Model):
    #parent = models.ForeignKey('SpideredUrl', null=True)
    url = models.URLField(max_length=1000, unique=True, db_index=True)
    article = models.ForeignKey(Article, null=True)
    url_signature = models.ForeignKey(UrlSignature, null=True)  # null only for loading


class ShareWarsUrl(models.Model):
    id = models.BigIntegerField(primary_key=True)
    spidered = models.ForeignKey(SpideredUrl, null=True)  # null only for loading
    when = models.DateTimeField(null=True, help_text='spider time')
