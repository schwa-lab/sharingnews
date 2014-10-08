from __future__ import division, absolute_import, print_function
import datetime
from collections import defaultdict

from lxml import etree

from jsonview.decorators import json_view
from django.shortcuts import render_to_response, redirect, get_object_or_404
from django.http import Http404, HttpResponseBadRequest
from django.template import RequestContext
from django.core.urlresolvers import reverse

from .models import SpideredUrl, Article, DownloadedArticle, UrlSignature, css_to_xpath
from .scraping import extractions_as_unicode


def article(request, id):
    article = get_object_or_404(Article, id=id)
    return render_to_response('article.html',
                              {'article': article,
                               'extracted_fields': DownloadedArticle.EXTRACTED_FIELDS},
                              context_instance=RequestContext(request))


def _article_by_spidered_url(**kwargs):
    obj = get_object_or_404(SpideredUrl, **kwargs)
    if obj.article is None:
        raise Http404  # TODO: make more informative
    return redirect(obj.article)


def article_by_swid(request, swid):
    return _article_by_spidered_url(sharewarsurl__id=swid)


def article_by_url(request, url):
    return _article_by_spidered_url(url=url)


def _parse_month(s):
    """Returns the start and stop of the month/year string"""
    n = int(s)
    if len(s) == 4:
        return datetime.date(n, 1, 1), datetime.date(n + 1, 1, 1)
    elif len(s) == 6:
        y, m = divmod(n, 100)
        return datetime.date(y, m, 1), datetime.date(y if m < 12 else y + 1, m + 1 if m < 12 else 1, 1)
    raise ValueError('Could not parse {!r} as a year/month'.format(s))


def collection(request, sig=None, period=None, start=None, end=None):
    articles = Article.objects.all()
    if period:
        assert start is None and end is None
        _ps, _pe = _parse_month(period)
        articles = articles.filter(fb_created__gte=_ps, fb_created__lt=_pe)
    elif start:
        articles = articles.filter(fb_created__gte=_parse_month(start)[0])
    elif end:
        articles = articles.filter(fb_created__lt=_parse_month(end)[1])

    if sig is None:
        subdivisions = articles.domain_frequencies()
        breadcrumbs = []
    elif '/' not in sig:
        # Is just base_domain
        sigs = UrlSignature.objects.for_base_domain(sig)
        if sigs.count() == 0:
            raise Http404
        articles = articles.filter(url_signature__in=sigs)
        subdivisions = articles.signature_frequencies()
        breadcrumbs = [None]
    else:
        sig_obj = get_object_or_404(UrlSignature, signature=sig)
        articles = articles.filter(url_signature=sig_obj)
        subdivisions = None
        breadcrumbs = [None, sig_obj.base_domain]

    N = articles.count()

    # hide insignificant subdivisions
    if subdivisions:
        # append coverage percentage
        tmp = []
        cumtotal = 0
        for subdiv, count in subdivisions:
            cumtotal += count
            tmp.append((subdiv, count, 100 * cumtotal / N))
        subdivisions = tmp

        target_coverage = 99.9
        for i, entry in enumerate(subdivisions):
            if entry[2] > target_coverage:
                i += 1
                while i < len(subdivisions) and subdivisions[i] == subdivisions[i-1][1]:
                    i += 1
                subdivisions = subdivisions[:i + 1]
                break

    #percentages = [50, 75, 90, 95, 99]
    #bins = articles.calc_share_quantiles(percentages)
    bins = [0, 1, 10, 100, 1000, 10000, 100000, 1000000]

    bin_data = (articles.bin_shares(bins).values('binned_shares')
                        .annotate_stats('total_shares').order_by('min'))
    bin_data = list(bin_data)
    for i, entry in enumerate(bin_data):
        if entry['count'] == 0:
            bin_data = bin_data[:i]
            break
        entry['example'] = (articles.bin_shares(bins)
                                    .filter(total_shares__gte=entry['min'],
                                            total_shares__lte=entry['max'])[0])  # order_by('?') is expensive

    fetched = articles.filter(fetch_status__isnull=False)
    fetched_success = fetched.filter(fetch_status__gte=200, fetch_status__lt=300)
    dev_sample = fetched_success.filter(downloaded__in_dev_sample=True)

    # TODO fetch stats and render page
    return render_to_response('collection.html',
                              {'params': {'sig': sig,
                                          'start': start,
                                          'end': end,
                                          'period': period},
                               'breadcrumbs': breadcrumbs,
                               'share_bins': bin_data,
                               'subdivisions': subdivisions,
                               'articles': articles,
                               'fetched': fetched,
                               'fetched_success': fetched_success,
                               'dev_sample': dev_sample},
                              context_instance=RequestContext(request))


def get_extractor(request, signature, field):
    selector = request.GET.get('selector') or getattr(signature, field + '_selector') or ''
    eval_on_load = request.GET.get('autoeval')
    articles = signature.article_set
    dev_sample = articles.filter(downloaded__in_dev_sample=True)
    #domain_sigs = articles.filter(url_signature__base_domain=signature.base_domain).signature_frequencies()
    return render_to_response('extractor.html',
                              {'params': {'sig': signature.signature, 'field': field},
                               'fields': DownloadedArticle.EXTRACTED_FIELDS,
                               'selector': selector,
                               'eval_on_load': eval_on_load,
                               'dev_sample': dev_sample,
                               #'domain_sigs': domain_sigs,
                               },
                              context_instance=RequestContext(request))


def post_extractor(request, signature, field):
    if 'selector' not in request.POST:
        return HttpResponseBadRequest('Expected selector parameter')
    selector = request.POST.get('selector')
    try:
        signature.set_selector(field, selector)
    except Exception as e:
        return HttpResponseBadRequest('Error in setting selector and converting to XPath: {!r}'.format(e))
    signature.save()
    return redirect(reverse('extractor',
                            kwargs={'field': field, 'sig': signature.signature}))


def extractor(request, sig, field=DownloadedArticle.EXTRACTED_FIELDS[0]):
    if field not in DownloadedArticle.EXTRACTED_FIELDS:
        raise Http404('Field {} unknown. Expected one of {}'.format(field, DownloadedArticle.EXTRACTED_FIELDS))
    signature = get_object_or_404(UrlSignature, signature=sig)
    if request.method.lower() == 'post':
        return post_extractor(request, signature, field)
    else:
        return get_extractor(request, signature, field)


@json_view
def extractor_eval(request, sig):
    # allow multiple sels
    selectors = request.GET.getlist('selector')
    # error if none or too many
    signature = get_object_or_404(UrlSignature, signature=sig)
    dev_sample = signature.article_set.filter(downloaded__in_dev_sample=True).select_related('downloaded')
    xpaths = [(selector, etree.XPath(css_to_xpath(selector))) for selector in selectors]
    results = defaultdict(dict)
    for article in dev_sample:
        parsed = article.downloaded.parsed_html
        for selector, xpath in xpaths:
            # XXX: need correct test for element
            results[selector][article.id] = extractions_as_unicode(xpath(parsed))
    return results


@json_view
def prior_extractors(request, field, sig):
    """Get frequency of selectors previously saved"""
    signature = get_object_or_404(UrlSignature, signature=sig)
    signatures = UrlSignature.objects.exclude(id=signature.id)
    field += '_selector'
    results = [{'selector': k,
                'overall': v,
                'overall_example': signatures.filter(**{field: k})[0].signature,
                }
               for k, v
               in signatures.all().count_field(field)]

    domain_mapping = dict(signatures.filter(base_domain=signature.base_domain).count_field(field))
    for entry in results:
        sel = entry['selector']
        if sel not in domain_mapping:
            continue
        entry['domain'] = domain_mapping[sel]
        entry['domain_example'] = signatures.filter(**{'base_domain': signature.base_domain,
                                                       field: sel})[0].signature

    # TODO: match path but possibly different domain

    return {'data': results}
