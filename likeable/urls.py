from django.conf.urls import patterns, include, url
from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin

MONTH_PATTERN = '201[0-9](?:[01][0-9])?'

js_info_dict = {
###        'domain': 'likeable',
###        'packages': ('likeable',),
}


urlpatterns = patterns('',
    url(r'^article/(?P<id>[0-9]+)$', 'likeable.views.article', name='article'),
    url(r'^article/(?P<id>[0-9]+)/raw$', 'likeable.views.article_raw', name='article_raw'),
    url(r'^article/sw/(?P<swid>[0-9]+)$', 'likeable.views.article_by_swid', name='article_by_swid'),  # problematic given deduplication
    url(r'^article/url/(.+)$', 'likeable.views.article_by_url', name='article_by_url'),
    url(r'^/?$', 'likeable.views.collection', name='collection'),
    url(r'^collection/(?P<start>{m})?-(?P<end>{m})?(?:/(?P<sig>.+))?$'.format(m=MONTH_PATTERN), 'likeable.views.collection', name='collection'),
    #url(r'^collection/(?P<period>{})(?:/(?P<sig>.+))?$'.format(MONTH_PATTERN), 'likeable.views.collection', name='collection-period'),

    url(r'^extractor/(?P<field>\w+)/(?P<sig>.+)', 'likeable.views.extractor', name='extractor'),
    url(r'^extractor-eval/(?P<sig>.+)', 'likeable.views.extractor_eval', name='extractor_eval'),
    url(r'^extractor-report', 'likeable.views.extractor_report', name='extractor_report'),
    url(r'^prior-extractors/(?P<field>[a-z_0-9]+)/(?P<sig>.+)', 'likeable.views.prior_extractors', name='prior_extractors'),
    url(r'^export(?:/)?', 'likeable.views.export', name='export'),

    url(r'^admin/', include(admin.site.urls)),
    url(r'^jsi18n/$', 'django.views.i18n.javascript_catalog', js_info_dict),
) + static(settings.STATIC_URL, name='static')
