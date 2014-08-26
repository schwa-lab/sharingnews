import re


def url_signature(url):
    url = url.split('#')[0]
    if '?' in url:
        url, query = url.split('?', 1)
        query = '&'.join(x.split('=')[0] for x in query.split('&'))
    else:
        query = ''
    _, url = url.split('://', 1)
    url = url.rstrip('/')
    if '/' in url:
        domain, path = url.split('/', 1)
    else:
        domain = url
        path = ''
    path = re.sub('[0-9]', '0', path)
    path = re.sub('[0-9a-zA-Z_\'",$-]*[a-zA-Z]+[0-9a-zA-Z_\'",$-]*', 'a', path)
    if domain.startswith('www.'):
        domain = domain[4:]
    return domain, path, query

