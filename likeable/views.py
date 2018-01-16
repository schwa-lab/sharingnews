from __future__ import division, absolute_import, print_function
import datetime
from collections import defaultdict
import re
from xml.sax.saxutils import escape as xml_escape
import random
import itertools
import operator

from jsonview.decorators import json_view
from django.shortcuts import render_to_response, redirect, get_object_or_404
from django.http import Http404, HttpResponseBadRequest, HttpResponse
from django.template import RequestContext
from django.core.urlresolvers import reverse
from django.templatetags.static import static
from django.db.models import F
from sklearn.externals.joblib import Parallel, delayed

from .models import SpideredUrl, Article, DownloadedArticle, UrlSignature, dev_sample_diagnostics
from .scraping import extract
from .cleaning import compress_html, insert_base_href
from .view_helpers import send_zipfile
from .export import gen_export_folders
from .forms import ExportForm


def article(request, id):
    article = get_object_or_404(Article, id=id)
    return render_to_response('article.html',
                              {'article': article,
                               'breadcrumbs': [None, article.url_signature.base_domain, article.url_signature.signature],
                               'extracted_fields': DownloadedArticle.EXTRACTED_FIELDS},
                              context_instance=RequestContext(request))


def article_raw(request, id):
    downloaded = get_object_or_404(DownloadedArticle, article_id=id)
    html = compress_html(downloaded.html)
    style = request.GET.get('style')
    debug = request.GET.get('debug')

    html = insert_base_href(html, downloaded.article.url)

    if style == 'none':
        html = re.sub(r'(?i)<link[^>]*\brel=(["\']?)stylesheet[^>]*>', '', html)
    if debug:
        SELECTOR_CONTENT = ('<link rel="stylesheet" href="{}">'
                            '<script type="text/javascript" src="{}"></script>'.format(
                                request.build_absolute_uri(static('css/css-debug.css')),
                                request.build_absolute_uri(static('js/css-debug.js'))))
        match = re.search('(?i)</html>', html)
        if match is not None:
            ins = match.start()
        else:
            ins = html.index('>') + 1
        html = html[:ins] + SELECTOR_CONTENT + html[ins:]
    return HttpResponse(html)


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
        articles = articles.filter(spider_when__gte=_ps, spider_when__lt=_pe)
    elif start:
        articles = articles.filter(spider_when__gte=_parse_month(start)[0])
    elif end:
        articles = articles.filter(spider_when__lt=_parse_month(end)[1])

    if sig is None:
        # Tuple extended for signature object included below
        subdivisions = [tup for tup in articles.domain_frequencies()]
        domain_sigs = {sig.base_domain: sig for sig in UrlSignature.objects.filter(base_domain__in=[tup[0] for tup in subdivisions]).domain_defaults()}
        subdivisions = [tup + (domain_sigs[tup[0]] if tup[0] else None,) for tup in subdivisions]
        breadcrumbs = []
    elif '/' not in sig:
        # Is just base_domain
        sigs = UrlSignature.objects.for_base_domain(sig)
        if sigs.count() == 0:
            raise Http404
        articles = articles.filter(url_signature__in=sigs)
        subdivisions = articles.signature_frequencies(return_id=True)
        # XXX: Can use only() if necessary
        lookup = UrlSignature.objects.in_bulk([tup[0] for tup in subdivisions])
        subdivisions = [(lookup[tup[0]].signature,) + tup[1:] + (lookup[tup[0]],)
                        for tup in subdivisions]
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
        for subdiv, count, sig_obj in subdivisions:
            cumtotal += count
            tmp.append((subdiv, count, 100 * cumtotal / N, sig_obj))
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

    bin_data = (articles.bin_shares(bins, shares_field='fb_count_5d').values('binned_shares')
                        .annotate_stats('fb_count_5d').order_by('min'))
    bin_data = list(bin_data)
    for i, entry in enumerate(bin_data):
        if entry['count'] == 0:
            bin_data = bin_data[:i]
            break
        examples = (articles#.bin_shares(bins)
                            .filter(fb_count_5d__gte=entry['min'],
                                    fb_count_5d__lte=entry['max'])[:1])  # order_by('?') is expensive
        examples = list(examples)
        if examples:
            entry['example'] = examples[0]
        else:
            print('No example for, entry')

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

# XXX: belongs in models
EXTRACTED_SQL = ' || '.join('CASE WHEN likeable_downloadedarticle.{} IS NOT NULL THEN \'{}\' ELSE \'\' END'.format(*tup) for tup in [
    ('headline', 'H'),
    ('dateline', 'D'),
    ('byline', 'B'),
    ('body_text', 'T'),
])


def _space_out(selector):
    selector = selector or ''
    if '\n' not in selector:
        selector = selector.replace(';', ';\n')
        selector = selector.replace('\n ', '\n')
    return selector


def get_extractor(request, signature, field):
    selector = _space_out(request.GET.get('selector') or signature.get_selector(field))
    backoff = _space_out(signature.get_backoff().get(field))
    eval_on_load = request.GET.get('autoeval', False)
    articles = signature.dev_articles
    dev_sample = _sample(articles.only('id', 'title', 'spider_when', 'url_signature__base_domain', 'downloaded__structure_group').extra(select={'extracted': EXTRACTED_SQL}), stratify='downloaded__structure_group')
    #domain_sigs = articles.filter(url_signature__base_domain=signature.base_domain).signature_frequencies()
    return render_to_response('extractor.html',
                              {'params': {'sig': signature.signature,
                                          'field': field,
                                          'msg': request.GET.get('msg')},
                               'fields': {f: signature.get_selector(f) for f in DownloadedArticle.EXTRACTED_FIELDS},
                               'selector': selector,
                               'backoff': backoff,
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
        success = signature.set_selector(field, selector)
    except Exception as e:
        return HttpResponseBadRequest('Error in setting selector and converting to XPath: {!r}'.format(e))
    signature.save()
    if success:
        msg = 'Selector%20saved%20and%20marked%20for%20re-extraction'
    else:
        msg = 'No%20change:%20not%20marked%20for%20re-extraction.'
    return redirect(reverse('extractor',
                            kwargs={'field': field, 'sig': signature.signature}) +
                    '?msg=' + msg)


def extractor(request, sig, field='body_text'):
    if field not in DownloadedArticle.EXTRACTED_FIELDS:
        raise Http404('Field {} unknown. Expected one of {}'.format(field, DownloadedArticle.EXTRACTED_FIELDS))
    signature = get_object_or_404(UrlSignature, signature=sig)
    if request.method.lower() == 'post':
        return post_extractor(request, signature, field)
    else:
        return get_extractor(request, signature, field)


def _extractor_eval(selectors, articles):
    res = []
    for article in articles:
        parsed = article.downloaded.parsed_html
        res.append([extract(selector, parsed, as_unicode=True, return_which=True)
                    for selector in selectors])
    return res


def _sample(entries, n=200, rng=None, stratify=None, stratify_prop=.5):
    if rng is None:
        rng = random.Random(42)
    entries = list(entries.order_by('pk'))
    if len(entries) > n:
        if stratify is None:
            entries = rng.sample(entries, n)
        else:
            get = operator.attrgetter(stratify.replace('__', '.'))
            groups = defaultdict(list)
            for entry in entries:
                groups[get(entry)].append(entry)
            sampled = []
            n_per_group = max(int(n * stratify_prop) // len(groups), 1)
            print('n_per_group', n_per_group)
            for group in groups.values():
                if len(group) > n_per_group:
                    sampled.extend(rng.sample(group, n_per_group))
                else:
                    sampled.extend(group)
            remainder = n - len(sampled)
            if remainder > 0:
                sampled.extend(rng.sample(set(entries) - set(sampled), remainder))
            entries = sampled

    return entries


@json_view
def extractor_eval(request, sig):
    # allow multiple sels
    selectors = request.GET.getlist('selector')
    # error if none or too many
    signature = get_object_or_404(UrlSignature, signature=sig)
    dev_sample = _sample(signature.dev_articles.only('id', 'downloaded__html', 'downloaded__structure_group'), stratify='downloaded__structure_group')
    results = defaultdict(dict)
    # FIXME: find more robust way to set n_jobs
    N_JOBS = min(10, len(dev_sample))
    para = Parallel(n_jobs=N_JOBS, backend='threading', verbose=10)
    chunk_size = (len(dev_sample) + N_JOBS - 1) // N_JOBS
    # prepare cache first:
    for selector in selectors:
        extract(selector)
    results = para(delayed(_extractor_eval)(selectors, dev_sample[i * chunk_size:(i + 1) * chunk_size]) for i in range(N_JOBS))
    results = list(itertools.chain(*results))
    results = {selector: {article.id: extraction
                          for article, extraction in zip(dev_sample, sel_results)}
               for selector, sel_results in zip(selectors, zip(*results))}
    return results


@json_view
def prior_extractors(request, field, sig):
    """Get frequency of selectors previously saved

    Note: values are HTML-escaped thanks to datatables
    """
    signature = get_object_or_404(UrlSignature, signature=sig)
    signatures = UrlSignature.objects.exclude(id=signature.id)
    field += '_selector'
    results = [{'selector': k,
                'append': '',
                'overall': v,
                'example': signatures.filter(**{field: k})[0].signature,
                }
               for k, v
               in signatures.all().count_field(field)]

    domain_mapping = dict(signatures.filter(base_domain=signature.base_domain).count_field(field))
    for entry in results:
        sel = entry['selector']
        if sel not in domain_mapping:
            continue
        entry['domain'] = domain_mapping[sel]
        entry['example'] = signatures.filter(**{'base_domain': signature.base_domain,
                                                field: sel})[0].signature

        for k, v in entry.items():
            if isinstance(v, (str, unicode)):
                entry[k] = xml_escape(v)

    for entry in results:
        entry['selector'] = _space_out(entry['selector'])

    # TODO: match path but possibly different domain

    return {'data': results}


def extractor_report(request):
    min_n_articles = int(request.GET.get('min_n_articles', 100))
    min_n_dev = int(request.GET.get('min_n_dev', 5))
    print(repr((min_n_articles, min_n_dev)))
    def get_rows():
        for sig, sgroup, n_articles, n_dev, diagnostics in dev_sample_diagnostics():
            if n_articles < min_n_articles:
                continue
            if n_dev < min_n_dev:
                continue
            for field in DownloadedArticle.EXTRACTED_FIELDS:
                yield sig, sgroup, n_articles, n_dev, field, sig.get_selector(field), {k: v / n_dev * 100 for k, v in diagnostics[field].iteritems()}
    return render_to_response('extractor-report.html',
                              {'columns': DownloadedArticle.DIAGNOSTIC_EXTRAS,
                               'rows': get_rows()},
                              context_instance=RequestContext(request))


# TODO: perhaps move to models.Article
MEASURE_FIELDS = {
    'fb-total-longterm': F('fb_count_longterm'),
    'fb-total-5d': F('fb_count_5d'),
}

# XXX: this may belong in models
def _group_for_export(grouping='topn', measure='fb-total-longterm', exclude_domains=None, domains=None, start_date=None,
                      end_date=None, contains=None, topn_param=[100],
                      sample='undersample', sample_atmost=None, sample_percent=None,
                      fetched_only=True, ignore_fb_zeros=True, **kwargs):
    articles = Article.objects.all()
    # HACK: Exclude domain root as non-article
    articles = articles.exclude(url_signature__signature__regex='^[^/]*//$')
    if fetched_only:
        articles = articles.filter(downloaded__isnull=False)
    if ignore_fb_zeros:
        articles = articles.filter(fb_count_longterm__gt=0)

    if domains is not None:
        articles = articles.filter(url_signature__base_domain__in=domains)
    if exclude_domains is not None:
        articles = articles.exclude(url_signature__base_domain__in=exclude_domains)

###    if start_date is not None:
###        # TODO: date search once date is stored as timestamp
###        articles = articles.filter(downloadedarticle__)
###    if end_date is not None:
###        # TODO: date search once date is stored as timestamp
###        articles = articles.filter(downloadedarticle__)
###    if contains is not None:
###        # TODO: full-text search once tsvector is stored
###        articles = articles.filter()

    measure = MEASURE_FIELDS[measure]
    # Requires Django 1.8:
    articles = articles.annotate(measure=measure).order_by('-measure')

    articles = articles.values_list('id', 'measure')

    # apply any immediate limitations
    if grouping == 'topn':
        # topn_param should be ascending list of ints
        articles = list(articles[:topn_param[-1]])
        groups = []
        for start, stop in zip([0] + topn_param, topn_param):
            groups.append(articles[start:stop])

    # Groups should be lists by now...

    rng = random.Random(42)
    if sample in ('undersample', 'atmost'):
        if sample == 'undersample':
            sample_atmost = min(map(len, groups))
        sample_atmost = itertools.repeat(sample_atmost)
    elif sample == 'percent':
        sample_atmost = (int(sample_percent / 100 * len(group) + .5) for group in groups)
    if sample_atmost is not None:
        groups = [_downsample(rng, group, atmost)
                  for group, atmost in zip(groups, sample_atmost)]
    print('Group lengths', [len(g) for g in groups])
    return groups


def _downsample(rng, articles, sample_size):
    """Reservoir sample while maintaining sorted order"""
    reservoir = articles[:sample_size]
    n = sample_size
    for art in articles[sample_size:]:
        n += 1
        i = int(rng.random() * n)
        if i < sample_size:
            del reservoir[i]
            reservoir.append(art)
    return reservoir


def _get_export_contents(groups, queryset):
    for group in groups:
        # FIXME: This could be very memory-intensive
        # Needs to be a generator, with batched queries of limited size
        lookup = queryset.objects.in_bulk([article_id
                                           for article_id, measure in group])
        out = []
        for article_id, measure in group:
            article = lookup[article_id]
            if isinstance(article, dict):
                article['measure'] = measure
            else:
                article.measure = measure
            out.append(article)
        yield out


excluded_domains = '''
buzzfeed.com
cracked.com
gawker.com
go.com
godvine.com
huffingtonpost.com
jezebel.com
mashable.com
msn.com
petflow.com
pogo.com
slate.com
techcrunch.com
theconversation.com
thedailybeast.com
thoughtcatalog.com
tmz.com
trueactivist.com
twitter.com
vimeo.com
vizcio.com
yahoo.com
youtube.com

?brisbanetimes.com.au
?businessinsider.com.au
?politico.com

?ew.com
?forbes.com
?hollywoodreporter.com
?people.com
?rollingstone.com
?time.com
?vanityfair.com
?theatlantic.com

?repubblica.it
?corriere.it

npr.org
today.com
'''


def post_export(request, data):
    # TODO: save as preset
    # TODO: async thread and response with "check status here" link
###    groups = _group_for_export(**data)
    groups = _group_for_export(exclude_domains=excluded_domains.replace('?', '').split(), topn_param=[200])
    # groups is a list of lists of (article_id, measure) pairs
    if data.get('exportlisting'):
        articles = Article.objects.only('id', 'title', 'url', 'url_signature').prefetch_related('url_signature')
    elif data.get('exportfolders'):
        articles = Article.objects.all()
    # TODO: alternatives

    ### XXX: design is hard until we know how these things are being output
    # Dropbox requires auth process, as well as way of notifying user the job is done
    # May also be able to upload zip concurrent with building

    # Each exporter can generate files, and zipping logic can be external, but do we need an approach that can return a page to viewer?
    # ZipFile can either write locally, or can write to a DropBox chunked uploader
    return send_zipfile(request, gen_export_folders(groups, articles), 'export.zip')



def export(request):
    # FIXME FIXME FIXME
    if request.method == 'POST':
        form = ExportForm(request.POST)
        if form.is_valid():
            return post_export(request, form.cleaned_data)
    else:
        preset = request.GET.get('preset')
        if preset is None:
            form = ExportForm()
        else:
            # TODO: load
            pass
    # TODO: load list of presets
    return render_to_response('export.html', {'form': form},
                              context_instance=RequestContext(request))
