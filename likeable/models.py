# -*- coding: utf-8 -*-

from __future__ import print_function, absolute_import, division
import re
import logging
import datetime
import urllib
from collections import Counter, defaultdict, namedtuple
import itertools
import operator
import random

import pytz
from lxml import etree
from readability import readability
from django.db import models
from django.core.urlresolvers import reverse
from dateutil.parser import parse as parse_date
import requests

from .cleaning import xml_unescape, compress_html, extract_facebook_canonical, unicode_from_www
from .scraping import extract, DEFAULT_CODE, DOMAIN_DEFAULT_CODE, fetch_with_refresh, get_mime, FetchException
from .models_helpers import IntArrayField
from .structure import sketch_doc


logger = logging.getLogger(__name__)


def utcnow():
    return datetime.datetime.utcnow().replace(tzinfo=pytz.utc)


class UrlSignatureQS(models.query.QuerySet):
    def count_field(self, field):
        return self.filter(**{field + '__isnull': False})\
                   .values_list(field)\
                   .annotate(n=models.Count('pk'))

    def get_structure_group_counts(self, min_freq=5):
        for sig_id, entries in itertools.groupby(DownloadedArticle.objects.filter(article__url_signature__in=self, structure_group__isnull=False).values_list('article__url_signature', 'structure_group').annotate(n=models.Count('pk')).filter(n__gte=min_freq).order_by('article__url_signature__id', '-n'), operator.itemgetter(0)):
            yield sig_id, [entry[1:] for entry in entries]

    def update_structure_group_counts(self, up_to=5, min_freq=5):
        for sig_id, entries in self.get_structure_group_counts(min_freq):
            groups = [group for group, n in entries[:up_to]]
            if not groups:
                groups = None
            UrlSignature.objects.filter(pk=sig_id).update(structure_groups=','.join(map('{:d}'.format, groups)))

    def domain_defaults(self):
        return self.filter(signature=models.F('base_domain'))

    def has_domain_default(self):
        """Filter to sigs that have selector defaulting to domain default"""
        if hasattr(self, '_has_domain_default_q'):
            return self.filter(self._has_domain_default_q)
        q = models.Q()
        for f in EXTRACTED_FIELDS:
            q |= models.Q(**{f + '_selector__startswith': DOMAIN_DEFAULT_CODE})
        self._has_domain_default_q = q
        return self.has_domain_default()

    def has_default(self):
        """Filter to sigs that have selector defaulting to default"""
        if hasattr(self, '_has_default_q'):
            return self.filter(self._has_default_q)
        q = models.Q()
        for f in EXTRACTED_FIELDS:
            q |= models.Q(**{f + '_selector__startswith': DEFAULT_CODE})
        self._has_default_q = q
        return self.has_default()


class UrlSignatureManager(models.Manager):
    def get_queryset(self):
        return UrlSignatureQS(self.model)

    def for_base_domain(self, domain):
        return self.filter(base_domain=domain)

    def get_domain_default(self, domain):
        try:
            return self.for_base_domain(domain).domain_defaults()[0]
        except IndexError:
            return None


def get_domains():
    return UrlSignature.objects.filter(base_domain__contains='.').values_list('base_domain', flat=True).distinct().order_by('base_domain')


def _make_extractor(field):
    def _extractor(self, doc, as_unicode=False):
        return extract(self.get_selector(field), doc, as_unicode)
    _extractor.__name__ = 'extract_' + field
    return _extractor


_empty_doc = etree.fromstring('<x></x>')


EXTRACTED_FIELDS = {'headline': 'H', 'dateline': 'D', 'byline': 'B', 'body_text': 'T',}# 'body_html': 'M'}

class UrlSignature(models.Model):
    objects = UrlSignatureManager()
    signature = models.CharField(max_length=256, unique=True, db_index=True)  # not sure if it's a good idea to use this as a string primary key. would make SpideredUrl big.
    base_domain = models.CharField(max_length=50, db_index=True)  # oversized due to broken data :(

    # HACK: we allow signature==base_domain for special instances that should
    # not correspond directly to any articles (lacks /s). This allows us to
    # set default extractors per-domain.
    @property
    def is_domain_default(self):
        return self.base_domain == self.signature

    modified_when = models.DateTimeField(default=utcnow)  # selectors modified at this timestamp

    # Up to 5 most prominent structure groups with at least 5 entries
    # XXX: should we store quantity too?
    structure_groups = models.CommaSeparatedIntegerField(max_length=15, null=True)

    # When updating defaults, run makemigrations, and scripts/reextract-defaults.py
    DEFAULT_SELECTORS = {
        'headline': DEFAULT_CODE + '((text))[itemprop~="headline"]; ((text))h1; [property~="og:title"]::attr(content)',
        'body_text': DEFAULT_CODE + '((text))[property~="articleBody"] > p;\n((text))[itemprop~="articleBody"] > p;\n((text))((readability.summary))p',
        'byline': DEFAULT_CODE + '((text))[itemprop~=author];\n((text)).hnews .author .fn;\n((text))[rel=author];((text)).byline',
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

    @property
    def dev_articles(self):
        if self.is_domain_default:
            articles = Article.objects.filter(url_signature__in=UrlSignature.objects.for_base_domain(self.base_domain))
        else:
            articles = self.article_set
        return articles.filter(downloaded__in_dev_sample=True)

    @property
    def status(self):
        out = ''
        for field, short in EXTRACTED_FIELDS.items():
            sel = self.get_selector(field)
            if sel is None:
                continue
            sel = sel.strip()
            if sel.startswith(DOMAIN_DEFAULT_CODE) or sel.startswith(DEFAULT_CODE):
                sel = re.sub('^({}|{})+'.format(DOMAIN_DEFAULT_CODE, DEFAULT_CODE), '', sel)
                if sel.strip():
                    out += short.lower()
            else:
                out += short
        return out

    def get_selector(self, field):
        return getattr(self, field + '_selector')

    @property
    def all_selectors(self):
        # useful in templates
        return {field: self.get_selector(field) for field in EXTRACTED_FIELDS}

    def update_defaults(self):
        return self._update_defaults(DEFAULT_CODE, self.DEFAULT_SELECTORS)

    def update_domain_defaults(self, domain_default=None):
        return self._update_defaults(DOMAIN_DEFAULT_CODE, self.get_backoff(domain_default))

    def _update_defaults(self, prefix, backoffs):
        updated = []
        for field in EXTRACTED_FIELDS:
            cur_sel = self.get_selector(field)
            if cur_sel is None or cur_sel.startswith(prefix):
                if self.set_selector(field, backoffs.get(field, prefix)):
                    updated.append(field)
        return updated

    def get_backoff(self, domain_default=None):
        if self.is_domain_default:
            return self.DEFAULT_SELECTORS
        if domain_default is None:
            domain_default = UrlSignature.objects.get_domain_default(self.base_domain)
        return {field: DOMAIN_DEFAULT_CODE + (domain_default.get_selector(field) or '')
                for field in EXTRACTED_FIELDS}

    def set_selector(self, field, value):
        if not value:
            value = None
        if value == getattr(self, field + '_selector'):
            return False

        if value.startswith(DOMAIN_DEFAULT_CODE) and self.is_domain_default:
            raise ValueError('Domain default signature cannot have '
                             'selector that defaults to domain default!')

        setattr(self, field + '_selector', value)
        # smoke test
        getattr(self, 'extract_' + field)(_empty_doc)
        self.set_modified()
        return True

    def set_modified(self):
        self._modified_set = True
        self.modified_when = utcnow()

    def save(self, *args, **kwargs):
        super(UrlSignature, self).save(*args, **kwargs)
        if self.is_domain_default and hasattr(self, '_modified_set'):
            i = 0
            for sig in UrlSignature.objects.for_base_domain(self.base_domain).has_domain_default():
                if sig.update_domain_defaults():
                    sig.save()
                i += 1
            logger.info('Updated %d downstream sigs for domain default @%s', i, self.base_domain)

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

    def __repr__(self):
        return '<UrlSignature: {0.signature} |{0.status}>'.format(self)


class BlacklistedUrl(models.Model):
    # URL that has been identified as non-article (in broad sense); content not useful
    url = models.URLField(max_length=256, primary_key=True)


class Site(models.Model):
    """Replicates a Likeable Engine table"""
    id = models.IntegerField(primary_key=True)
    name = models.TextField()
    url = models.URLField(max_length=256)
    rss_url = models.URLField(max_length=256, null=True)
    active = models.BooleanField()
    last_fetch = models.DateTimeField(null=True)
    health_start = models.DateTimeField(null=True)
    is_healthy = models.NullBooleanField()


SHARES_FIELDS = ['fb_count_initial', 'fb_count_2h', 'fb_count_1d',
                 'fb_count_5d', 'fb_count_longterm', 'tw_count_initial',
                 'tw_count_2h', 'tw_count_1d', 'tw_count_5d',
                 'tw_count_longterm']

# max known share count a little over 5e6
FINE_HISTOGRAM_BINS = [0] + [10 ** (i / 10.) for i in range(67)]

class ArticleQS(models.query.QuerySet):
    def calc_share_quantiles(self, percentiles=[50, 75, 90, 95, 99], shares_field='fb_count_longterm', return_count=False):  #  min_fb_created=None, max_fb_created=None):
        nonzero_shares = (self.filter(**{shares_field + '__gt': 0})
                              .values_list(shares_field, flat=True)
                              .order_by(shares_field))
        #N = nonzero_shares.count()
        nonzero_shares = list(nonzero_shares)
        N = len(nonzero_shares)
        import numpy as np
        result = np.exp(np.percentile(np.log(nonzero_shares), percentiles))
###        result =  [nonzero_shares[int(N * p / 100)]
###                   for p in percentiles]
        if return_count:
            return N, result
        else:
            return result

    def with_logs(self, shares_fields=SHARES_FIELDS):
        new_fields = {'log_' + f: 'LOG("likeable_article"."{}")'.format(f) for f in shares_fields}
        return self.extra(select=new_fields)

    def bin_shares(self, bin_max, field_name='binned_shares', shares_field='fb_count_longterm'):
        cases = ' '.join('WHEN {} <= {} THEN {}'.format(shares_field, int(m), i)
                         for i, m in enumerate(bin_max))
        return self.filter(**{shares_field + '__isnull': False}).extra(select={field_name: 'CASE {} ELSE {} END'.format(cases, len(bin_max))})

    def annotate_stats(self, field='fb_count_longterm'):
        return self.annotate(count=models.Count('pk'),
                             avg=models.Avg(field),
                             min=models.Min(field),
                             max=models.Max(field))

    def domain_frequencies(self):
        return self.values_list('url_signature__base_domain').annotate(count=models.Count('pk')).order_by('-count')

    def signature_frequencies(self, return_id=False):
        field = 'url_signature__signature' if not return_id else 'url_signature'
        return self.values_list(field).annotate(count=models.Count('pk')).order_by('-count')

    def for_base_domain(self, domain):
        return self.filter(url_signature__base_domain=domain)

    def close_scrapes(self, n_days=1):
        """Filter such that fb_created and sharewars crawling

        Note this may be indicative of when item was first shared / commented, but also other factors
        """
        # XXX: perhaps should use extra with ABS instead, but how to force joins?
        # abs(a - b) < 2 ==>  a <= b < 2 + a  or  b <= a < 2 + b
        d = datetime.timedelta(days=n_days)
        conds = [models.Q(**{f1 + '__gte': models.F(f2), f1 + '__lt': models.F(f2) + d})
                 for f1, f2 in [('spider_when', 'fb_created'),
                                ('fb_created', 'spider_when')]]
        return self.filter(conds[0] | conds[1])


class ArticleManager(models.Manager):
    def get_queryset(self):
        return ArticleQS(self.model)


def _random():
    # Picklable wrapper
    return random.random()


class Article(models.Model):
    objects = ArticleManager()

    # From Facebook's URL lookup
    id = models.BigIntegerField(null=False, primary_key=True,
                                help_text="Facebook's numeric ID")
    rand = models.FloatField(default=_random, help_text="Random number reproducable/fast random ordering")
    url_signature = models.ForeignKey(UrlSignature, null=True, db_index=True)  # null only when loading
    url = models.URLField(max_length=1000, db_index=True)  # canonical URL according to Facebook
    fb_updated = models.DateTimeField(null=True)
    fb_type = models.CharField(max_length=35, null=True)
    fb_has_title = models.BooleanField(default=False, db_index=True)  # for easy indexing
    title = models.CharField(max_length=1000, null=True)  # taken from Facebook scrape
    description = models.TextField(null=True)
    sharewars_site = models.ForeignKey(Site, null=True)

    fb_count_initial = models.PositiveIntegerField(null=True)
    fb_count_2h = models.PositiveIntegerField(null=True)
    fb_count_1d = models.PositiveIntegerField(null=True)
    fb_count_5d = models.PositiveIntegerField(null=True)
    fb_count_longterm = models.PositiveIntegerField(null=True)
    tw_count_initial = models.PositiveIntegerField(null=True)
    tw_count_2h = models.PositiveIntegerField(null=True)
    tw_count_1d = models.PositiveIntegerField(null=True)
    tw_count_5d = models.PositiveIntegerField(null=True)
    tw_count_longterm = models.PositiveIntegerField(null=True)

    spider_when = models.DateTimeField(null=True, db_index=True)
    fetch_status = models.IntegerField(null=True)
    # Special values of fetch_status:
    CUSTOM_FETCH_STATUS = {  # see likeable.scraping
        'bad content type': -111,
        'too many redirects': -1,
        'empty content': -2,
        'effectively empty content': -3,
        'timeout': -10,
        'server repeatedly unavailable': -503,
        'blacklisted': -200,  # fetch succeeded, but URL is homepage/portal
    }
    _accept_mime = {'text/html', 'application/xml', 'text/xml'}.__contains__  # accept without note
    _reject_mime = re.compile('^(application/pdf$|image/|audio/|video/)').match  # accept without note

    # fetch_when = models.DateTimeField(null=True)

    ### From FB id lookup
    fb_created = models.DateTimeField(null=True)
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

    def download(self, force=False, save=True, accept_encodings=None, user_agent_spoof='fb'):
        if self.fetch_status == 200 and self.downloaded is not None:  # FIXME: this second cond'n will raise an error
            if force:
                self.fetch_status = None
                self.downloaded.delete()
            else:
                return self.downloaded, None

        timestamp = utcnow()
        try:
            hops = fetch_with_refresh(self.url, accept_encodings, user_agent_spoof=user_agent_spoof)
        except FetchException as exc:
            if exc.code is not None:
                assert exc.code < 0
                self.fetch_status = exc.code
                if save:
                    self.save()
            raise

        response = hops[-1]
        self.fetch_status = response.status_code
        if self.fetch_status != 200:
            if save:
                self.save()
            return None, hops

        mime = get_mime(response)
        if not mime:
            logger.warning('No MIME when fetching', self)
        elif self._accept_mime(mime):
            pass
        elif self._reject_mime(mime):
            self.fetch_status = self.CUSTOM_FETCH_STATUS['bad content type']
            if save:
                self.save()
            return None, hops
        else:
            logger.warning('Unknown MIME {!r} when fetching {}'.format(mime, self))

        content = unicode_from_www(response)
        canonical = extract_facebook_canonical(content)
        if canonical is None:
            canonical = response.url
        if BlacklistedUrl.objects.filter(url=canonical).exists():
            self.fetch_status = self.CUSTOM_FETCH_STATUS['blacklisted']
            if save:
                self.save()
            return None, hops
        if canonical == self.url:
            canonical = None

        content = compress_html(content)

        downloaded = DownloadedArticle(article=self,
                                       html=content,
                                       fetch_when=timestamp,
                                       canonical_url=canonical,
                                       user_agent_spoof=user_agent_spoof)
        parsed = downloaded.parsed_html
        if parsed is not None:
            downloaded.structure_sketch = sketch_doc(parsed)
        # TODO: set flag that doc is empty
        if save:
            downloaded.save()
            self.save()
        return self.downloaded, hops

    def __repr__(self):
        return '<Article {}@{}>'.format(self.id, self.url)

    class Meta:
        index_together = [
            ('url_signature', 'spider_when'),
            ('fetch_status', 'url_signature'),
            ('fb_count_longterm', 'url_signature'),
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

    def delete(self, fetch_status=None):
        ids = list(self.values_list('article_id', flat=True))
        Article.objects.filter(pk__in=ids).update(fetch_status=fetch_status)
        return super(DownloadedArticleQS, DownloadedArticle.objects.filter(article_id__in=ids)).delete()


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
    canonical_url = models.TextField(null=True, db_index=True)
    user_agent_spoof = models.CharField(max_length=10, null=True)

    @property
    def needs_extraction(self):
        sig_modified = self.article.url_signature.modified_when
        if sig_modified is None:
            return False
        return self.scrape_when is None or self.scrape_when < sig_modified

    # sketches for clustering
    # array of 100 32-bit ints representing minhash over HTML paths
    structure_sketch = IntArrayField(null=True, db_index=True)
    structure_group = models.IntegerField(null=True)

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
        html = compress_html(html)  # Added 2015-03-04 to avoid javascript in extractions
        html = re.sub(u'[\x00\x01-\x08\x0b-\x0c\x0e-\x1f\x7f-\x84\ufffe\uffff]', u'', html)  # remove invalid XML1.0 chars
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
    site = models.ForeignKey(Site, null=True)
