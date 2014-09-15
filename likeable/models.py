
from __future__ import print_function, absolute_import, division
from django.db import models
from django.core.urlresolvers import reverse


class UrlSignatureManager(models.Manager):
    def for_base_domain(self, domain):
        return self.filter(base_domain=domain)


class UrlSignature(models.Model):
    objects = UrlSignatureManager()
    signature = models.CharField(max_length=256, unique=True, db_index=True)  # not sure if it's a good idea to use this as a string primary key. would make SpideredUrl big.
    base_domain = models.CharField(max_length=50, db_index=True)  # oversized due to broken data :(

    body_html_selector = models.CharField(max_length=1000, null=True)
    headline_selector = models.CharField(max_length=1000, null=True)
    dateline_selector = models.CharField(max_length=1000, null=True)
    byline_selector = models.CharField(max_length=1000, null=True)
    media_selector = models.CharField(max_length=1000, null=True)

    # require match zero or one object, except media_selector
    # when changed, rerun over signature dev articles; maybe should store stats with selectors


class WeekCountAggregate(models.sql.aggregates.Aggregate):
    is_ordinal = True
    sql_function = '' # unused
    sql_template = "COUNT(%(field)s)"


class WeekCount(models.aggregates.Aggregate):
    name = 'Week'
    def add_to_query(self, query, alias, col, source, is_summary):
        query.aggregates[alias] = WeekCountAggregate(col, source=source, 
            is_summary=is_summary, **self.extra)


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
    url = models.URLField(max_length=1000)  # canonical URL according to Facebook
    fb_updated = models.DateTimeField(null=True)
    fb_type = models.CharField(max_length=35, null=True)
    fb_has_title = models.BooleanField(default=False, db_index=True)  # for easy indexing
    title = models.CharField(max_length=1000, null=True)  # taken from Facebook scrape
    description = models.TextField(null=True)
    total_shares = models.PositiveIntegerField(null=True)  # tmp

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

    ### From our extraction
    in_dev_sample = models.BooleanField(default=False)
    download_path = models.CharField(max_length=1000, null=True)
    # scrape_when = models.DateTimeField(help_text='When we last scraped this content')
    #    # do we need another field to indicate our scraping method?
    headline = models.TextField(null=True)
    dateline = models.TextField(null=True)
    byline = models.TextField(null=True)
    body_html = models.TextField(null=True)  # should this be stored?
    # media = models.ManyToMany(MediaItem)
    # comments_data = models.OneToOne(CommentsData)

    # is_error_page = models.BooleanField(null=True)  # from extraction or inference

    ### From readability ??

    def get_absolute_url(self):
        return reverse('likeable.views.article', kwargs={'id': self.id})

    def read_html(self):
        # TODO: read from disk or fetch (cached or downloaded permanently)
        pass

    def get_meta_fields(self):
        # TODO: extract <meta name/content> pairs from read_html()
        pass

    def get_css_extractions(self):
        # TODO
        pass

    class Meta:
        index_together = [
            ('url_signature', 'fb_created'),
        ]



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
