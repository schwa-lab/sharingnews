from django.conf.urls import patterns, include, url
from django.contrib import admin

MONTH_PATTERN = '201[0-9](?:[01][0-9])?)'.format(YEAR_PATTERN)
MONTHRANGE_PATTERN = ('(?:(?P<period>{m})'
                      '|(?P<start>{m})?-(?P<end>{m})?'
                      ')'.format(m=MONTH_PATTERN, y=YEAR_PATTERN))

urlpatterns = patterns('',
    url(r'^article/(?P<id>[0-9]+)$', 'likeable.views.article', name='article'),
    url(r'^article/sw/(?P<swid>[0-9]+)$', 'likeable.views.article_by_swid', name='article_by_swid'),  # problematic given deduplication
    url(r'^article/url/(.+)$', 'likeable.views.article_by_url', name='article_by_url'),
    url(r'^collection/{}(?:/(?P<sig>.+))?$'.format(MONTHRANGE_PATTERN), 'likeable.views.collection', name='collection'),

    url(r'^admin/', include(admin.site.urls)),
)
