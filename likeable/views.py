
from .models import SpideredUrl, Article
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


def collection(request, sig=None, period=None, start=None, end=None):
    # TODO fetch stats and render page
    pass

