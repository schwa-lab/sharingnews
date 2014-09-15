
import datetime

from .models import SpideredUrl, Article, UrlSignature
from django.shortcuts import render_to_response, redirect, get_object_or_404
from django.http import Http404
from django.template import RequestContext

def article(request, id):
    article = get_object_or_404(Article, id=id)
    return render_to_response('article.html',
                              {'article': article},
                              context_instance=RequestContext(request))


def _article_by_spidered_url(**kwargs):
    obj = get_object_or_404(SpideredUrl, **kwargs)
    if obj.article is None:
        raise Http404  # TODO: make more informative
    return redirect(obj.article)


def article_by_swid(request, swid):
    return _article_by_spidered_url(swid=swid)


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

    N = articles.count()

    if sig is None:
        subdivisions = articles.domain_frequencies()
    elif '/' not in sig:
        # Is just base_domain
        sigs = UrlSignature.objects.for_base_domain(sig)
        if sigs.count() == 0:
            raise Http404
        articles = articles.filter(url_signature__in=sigs)
        subdivisions = articles.signature_frequencies()
    else:
        articles = articles.filter(url_signature=get_object_or_404(UrlSignature, signature=sig))
        subdivisions = None

    # hide insignificant subdivisions
    if subdivisions:
        subdiv_coverage = .99 * N
        coverage = 0
        for i, entry in enumerate(subdivisions):
            coverage += entry[1]  # count
            if coverage > subdiv_coverage:
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


    # TODO fetch stats and render page
    return render_to_response('collection.html',
                              {'params': {'sig': sig,
                                          'start': start,
                                          'end': end,
                                          'period': period},
                               'share_bins': bin_data,
                               'subdivisions': subdivisions},
                              context_instance=RequestContext(request))
