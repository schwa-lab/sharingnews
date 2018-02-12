from __future__ import print_function

import sys
import operator
import json
import binascii
from likeable.models import Article
from likeable.scraping import DOMAIN_DEFAULT_CODE, DEFAULT_CODE


get_when = operator.itemgetter('when')


def _iso8601(dt):
    if dt is None:
        return None
    return dt.isoformat()


def _drop_null(d):
    return {k: v for k, v in d.items() if v is not None}


REV_CUSTOM_FETCH_STATUS = {v: k for k, v
                           in Article.CUSTOM_FETCH_STATUS.items()}


def _format_fetch_status(fetch_status):
    if fetch_status is None:
        return None
    if fetch_status > 0:
        return 'HTTP %d' % fetch_status
    return REV_CUSTOM_FETCH_STATUS[fetch_status]


def _format_url_signature(article):
    try:
        return _format_fetch_status.cache[article.url_signature_id]
    except AttributeError:
        _format_fetch_status.cache = {}
    except KeyError:
        pass

    sig = article.url_signature
    out = {
        "signature": sig.signature,
        "domain": sig.base_domain,
        "modified_when": _iso8601(sig.modified_when),
        "selectors": {},
        "specificity": {},
    }
    if sig.structure_groups is not None:
        out['frequent_structure_groups'] = [int(x) for x in sig.structure_groups.split(',')]

    for name in ['body_html', 'body_text', 'headline', 'dateline', 'byline']:
        sel = getattr(sig, name + '_selector')
        if sel is None:
            continue
        spec = "signature"
        if sel.startswith(DOMAIN_DEFAULT_CODE):
            sel = sel[len(DOMAIN_DEFAULT_CODE):]
            spec = "domain"
        if sel.startswith(DEFAULT_CODE):
            sel = sel[len(DEFAULT_CODE):]
            spec = "global"
        out["selectors"][name] = sel
        out["specificity"][name] = spec

    _format_fetch_status.cache[article.url_signature_id] = out
    return out


def _format_counts(article, prefix):
    initial = getattr(article, prefix + '_count_initial')
    if initial is None:
        initial = 0
    c2h = getattr(article, prefix + '_count_2h')
    if c2h is None:
        c2h = initial
    c1d = getattr(article, prefix + '_count_1d')
    if c1d is None:
        c1d = c2h
    c5d = getattr(article, prefix + '_count_5d')
    if c5d is None:
        c5d = c1d
    out = {
        'initial': initial,
        '2h': c2h,
        '1d': c1d,
        '5d': c5d,
    }
    longterm = getattr(article, prefix + '_count_longterm')
    if longterm:
        out['longterm'] = longterm
    return out


def get_archive_json(article, exclude=None):
    out = {
        "facebook_id": article.id,
        "canonical_url": article.url,
        "facebook_metadata": _drop_null({
            "created": _iso8601(article.fb_created),
            "updated": _iso8601(article.fb_updated),
            "type": article.fb_type,
            "title": article.title,
            "description": article.description,
        }),
        "spider": sorted([
            {"url": spideredurl.url,
             "when": _iso8601(sharewarsurl.when),
             "likeable_id": sharewarsurl.id,
             "site_id": sharewarsurl.site.id if sharewarsurl.site is not None else None,
             "site_name": sharewarsurl.site.name if sharewarsurl.site is not None else None,
             "site_url": sharewarsurl.site.url if sharewarsurl.site is not None else None,
             }
            for spideredurl in article.spideredurl_set.all()
            for sharewarsurl in spideredurl.sharewarsurl_set.all()
        ], key=get_when),
        "count": {
            "facebook_shares": _format_counts(article, 'fb'),
            "binned_facebook_shares": _format_counts(article, 'binned_fb'),
            "binned_twitter_shares": _format_counts(article, 'binned_tw'),
            "twitter_shares": _format_counts(article, 'tw'),
        },
        "fetch": {
            "status": _format_fetch_status(article.fetch_status),
        }
    }
    try:
        down = article.downloaded
    except Exception:
        pass
    else:
        out["fetch"]["when"] = _iso8601(down.fetch_when)
        out["fetch"]["html"] = down.html
        if down.user_agent_spoof is not None:
            out["fetch"]["user_agent_spoof"] = down.user_agent_spoof

        out["scrape"] = {
            "url_group": _format_url_signature(article),
            "when": _iso8601(down.scrape_when),
            "in_dev_sample": down.in_dev_sample,
            "structure_sketch_hex": binascii.hexlify(down.structure_sketch) if down.structure_sketch is not None else None,
            "structure_group": down.structure_group,
        }
        out["extract"] = _drop_null({
            "body_html": down.body_html,
            "body_text": down.body_text,
            "lead": down.first_paragraph,
            "headline": down.headline,
            "dateline": down.dateline,
            "byline": down.byline,
        })

    if exclude:
        for path in exclude:
            blob = out
            try:
                for k in path[:-1]:
                    blob = blob[k]
                del blob[path[-1]]
            except KeyError:
                pass
    return json.dumps(out, indent=2, separators=(',', ': '))
