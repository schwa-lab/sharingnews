# TODO: note example responses
# TODO: wrap for multiple URLs, error-resilience, consistent response format
# TODO: raw fetches for facebook batch, linkedin, G+, etc. See https://gist.github.com/jonathanmoore/2640302
import requests
import time
import functools

from .secret import FB_API_TOKEN


def _str_to_list(obj):
    if isinstance(obj, (str, unicode, bytes)):
        return [obj]
    return list(obj)


# UNDERLYING API CALLS

def fetch_twitter(url):
    return requests.get('http://urls.api.twitter.com/1/urls/count.json', params={'url': url})


def fetch_facebook_rest(urls):
    return requests.get('http://api.ak.facebook.com/restserver.php',
                        params={'v': '1.0',
                                'method': 'links.getStats',
                                'format': 'json',
                                'urls': ','.join(urls)})


def fetch_facebook_ids(urls):
    if len(urls) > 50:
        raise ValueError('Facebook Graph API limits multiple ID requests to 50')
    return requests.get('https://graph.facebook.com/v2.2', params={'access_token': FB_API_TOKEN,
                                                                   'ids': ','.join(urls)})


def retry_until_success(fn=None, retries=10, wait=1):
    if fn is None:
        return functools.partial(retry_until_success, retries=retries, wait=wait)

    @functools.wraps(fn)
    def wrapper(*args, **kwargs):
        remaining = retries
        resp = fn(*args, **kwargs)
        while retries and resp.status_code >= 400:
            time.sleep(wait)
            resp = fn(*args, **kwargs)
            remaining -= 1
        return resp
    return wrapper
