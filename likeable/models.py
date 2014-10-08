
from __future__ import print_function, absolute_import, division
import re
import logging
import datetime
import pytz

from lxml import etree
from scrapy.selector import csstranslator
from readability import readability
from django.db import models
from django.core.urlresolvers import reverse

from .cleaning import xml_unescape

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


css_to_xpath = csstranslator.ScrapyHTMLTranslator().css_to_xpath


class _css_to_xpath_descriptor(object):
    def __init__(self, field):
        self.field = field

    def __get__(self, obj, objtype=None):
        if obj is None:
            return self
        css_sel = getattr(obj, self.field)
        if css_sel is None:
            return None
        # TODO: lrucache on objtype
        return css_to_xpath(css_sel)


class UrlSignature(models.Model):
    objects = UrlSignatureManager()
    signature = models.CharField(max_length=256, unique=True, db_index=True)  # not sure if it's a good idea to use this as a string primary key. would make SpideredUrl big.
    base_domain = models.CharField(max_length=50, db_index=True)  # oversized due to broken data :(

    modified_when = models.DateTimeField(default=utcnow)  # selectors modified at this timestamp
    body_html_selector = models.CharField(max_length=1000, null=True)
    body_text_selector = models.CharField(max_length=1000, null=True)
    headline_selector = models.CharField(max_length=1000, null=True)
    dateline_selector = models.CharField(max_length=1000, null=True)
    byline_selector = models.CharField(max_length=1000, null=True)
    media_selector = models.CharField(max_length=1000, null=True)

    def set_selector(self, field, value):
        if not value:
            value = None
        if value == getattr(self, field + '_selector'):
            return

        setattr(self, field + '_selector', value)
        # smoke test
        getattr(self, field + '_xpath')
        self.set_modified()

    def set_modified(self):
        self.modified_when = utcnow()

    # ?require match zero or one object, except media_selector
    # when changed, rerun over signature dev articles; maybe should store stats with selectors

    # Accessors for converted form
    body_html_xpath = _css_to_xpath_descriptor('body_html_selector')
    body_text_xpath = _css_to_xpath_descriptor('body_text_selector')
    headline_xpath = _css_to_xpath_descriptor('headline_selector')
    dateline_xpath = _css_to_xpath_descriptor('dateline_selector')
    byline_xpath = _css_to_xpath_descriptor('byline_selector')
    media_xpath = _css_to_xpath_descriptor('media_selector')

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
        return self.extra(select={field_name: 'CASE {} ELSE {} END'.format(cases, len(bin_max))})

    def annotate_stats(self, field='total_shares'):
        return self.annotate(count=models.Count('pk'),
                             avg=models.Avg(field),
                             min=models.Min(field),
                             max=models.Max(field))

    def domain_frequencies(self):
        return self.values_list('url_signature__base_domain').annotate(count=models.Count('pk')).order_by('-count')

    def signature_frequencies(self):
        return self.values_list('url_signature__signature').annotate(count=models.Count('pk')).order_by('-count')


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
        ]


class DownloadedArticle(models.Model):
    article = models.OneToOneField(Article, primary_key=True, related_name='downloaded')

    ### From our extraction
    in_dev_sample = models.BooleanField(default=False)
    html = models.TextField()  # fetched HTML content normed to UTF-8, with some lossy compression
    fetch_when = models.DateTimeField(null=True)
    scrape_when = models.DateTimeField(null=True)  # set to signature's modified_when, not scrape time
    canonical_url = models.TextField(null=True)

    EXTRACTED_FIELDS = ['headline', 'dateline', 'byline', 'body_text', 'body_html']
    headline = models.TextField(null=True)
    dateline = models.TextField(null=True)
    byline = models.TextField(null=True)
    body_text = models.TextField(null=True)
    body_html = models.TextField(null=True)  # should this be stored?
    # media = models.ManyToMany(MediaItem)
    # comments_data = models.OneToOneField(CommentsData)

    def _get_meta_fields(self):
        for tag in re.findall('(?i)<meta\s.*?>', self.html):
            name = re.search(r'(?i)\bname=(["\'])(.*?)\1', tag)  # TODO: support unquoted
            if name is None:
                continue
            name = name.group(2)
            content = re.search(r'(?i)\bcontent=(["\'])(.*?)\1', tag)  # TODO: support unquoted
            if content is None:
                logging.warn('Found name but no content in %s', tag)
            # todo: unescape
            yield name, xml_unescape(content.group(2))

    @property
    def meta_fields(self):
        return sorted(self._get_meta_fields())

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
