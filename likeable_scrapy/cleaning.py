import re


def url_signature(url):
    url = re.sub('[0-9]', '0', url)
    if '?' in url:
        url, query = url.split('?', 1)
        query = '&'.join(x.split('=')[0] for x in query.split('&'))
    else:
        query = ''
    _, url = url.split('://', 1)
    if '/' in url:
        domain, path = url.split('/', 1)
    else:
        domain = url
        path = ''
    path = re.sub('[a-zA-Z_-]+([0-9a-zA-Z_-]*)', 'a', path)
    if domain.startswith('www.'):
        domain = domain[4:]
    return domain, path, query

