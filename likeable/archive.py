import binascii
from likeable.models import Article
from likeable.scraping import DOMAIN_DEFAULT_CODE, DEFAULT_CODE


def _drop_null(d):
    return {k: v for k, v in d.items() if v is not None}


REV_CUSTOM_FETCH_STATUS = {v: k for k, v
                           in Article.CUSTOM_FETCH_STATUS.items()}


def _format_fetch_status(fetch_status):
    if fetch_status is None:
        return None
    if fetch_status > 0:
        return 'HTTP %d' % fetch_status
    return next(k for k, v in REV_CUSTOM_FETCH_STATUS
                if v == fetch_status)


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
        "modified_when": sig.modified_when,
        "selectors": {},
        "specificity": {},
    }
    if sig.frequent_structure_groups is not None:
        out['frequent_structure_groups'] = sig.frequent_structure_groups

    for name in ['body_html', 'body_text', 'headline', 'dateline', 'byline']:
        sel = getattr(sig, name + '_selector')
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


def get_archive_json(article):
    out = {
        "facebook_id": article.id,
        "canonical_url": article.url,
        "facebook_metadta": _drop_null({
            "created": article.fb_created,
            "updated": article.fb_updated,
            "type": article.fb_type,
            "title": article.title,
            "description": article.description,
        }),
        "spider": [
            {"url": spideredurl.url,
             "when": sharewarsurl.when,
             "likeable_id": sharewarsurl.id,
             "site_id": sharewarsurl.site.id,
             "site_name": sharewarsurl.site.name,
             "site_url": sharewarsurl.site.url,
             }
            for spideredurl in article.spideredurl_set
            for sharewarsurl in spideredurl.sharewarsurl_set
        ],
        "count": {
            "facebook_shares": _drop_null({
                "initial": article.fb_count_initial,
                "2h": article.fb_count_2h,
                "1d": article.fb_count_1d,
                "5d": article.fb_count_5d,
            }),
            "twitter_shares": _drop_null({
                "initial": article.tw_count_initial,
                "2h": article.tw_count_2h,
                "1d": article.tw_count_1d,
                "5d": article.tw_count_5d,
            })
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
        article["fetch"]["when"] = down.fetch_when
        article["fetch"]["html"] = down.html
        if down.user_agent_spoof is not None:
            article["fetch"]["user_agent_spoof"] = down.user_agent_spoof
        
        article["scrape"] = {
            "url_group": _format_url_signature(article),
            "when": down.scrape_when, 
            "in_dev_sample": down.in_dev_sample, 
            "structure_sketch_hex": binascii.hexlify(down.structure_sketch),
            "structure_group": down.structure_group,
        }
        article["extract"] = _drop_null({
            "body_html": down.body_html,
            "body_text": down.body_text,
            "headline": down.headline,
            "dateline": down.dateline,
            "byline": down.byline,
        })

    return out
