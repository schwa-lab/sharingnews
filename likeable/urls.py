from django.conf.urls import patterns, include, url
from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin

MONTH_PATTERN = '201[0-9](?:[01][0-9])?'

urlpatterns = patterns('',
    url(r'^article/(?P<id>[0-9]+)$', 'likeable.views.article', name='article'),
    url(r'^article/sw/(?P<swid>[0-9]+)$', 'likeable.views.article_by_swid', name='article_by_swid'),  # problematic given deduplication
    url(r'^article/url/(.+)$', 'likeable.views.article_by_url', name='article_by_url'),
    url(r'^collection/(?P<start>{m})?-(?P<end>{m})?(?:/(?P<sig>.+))?$'.format(m=MONTH_PATTERN), 'likeable.views.collection', name='collection'),
    #url(r'^collection/(?P<period>{})(?:/(?P<sig>.+))?$'.format(MONTH_PATTERN), 'likeable.views.collection', name='collection-period'),

    url(r'^extractors/(?P<sig>.+)', 'likeable.views.extractors', name='extractors'),
    url(r'^extractor-eval/(?P<sig>.+)', 'likeable.views.extractor_eval', name='extractor_eval'),
    url(r'^prior-extractors/(?P<field>[a-z_0-9]+)/(?P<sig>.+)', 'likeable.views.prior_extractors', name='prior_extractors'),

    url(r'^admin/', include(admin.site.urls)),
) + static(settings.STATIC_URL, name='static')
