import itertools
import re
import array

from lxml import etree
import xxhash
from joblib import Parallel, delayed
import numpy as np


def extract_paths(node, subcat_attribs=('class', 'property', 'itemprop')):
    prefix = (node.tag,)
    yield prefix
    for child in node.iterchildren():
        if isinstance(child.tag, str):
            for path in extract_paths(child, subcat_attribs):
                yield prefix + path

    attribs = node.attrib
    for attr_name in subcat_attribs:
        if attr_name in attribs:
            for val in attribs[attr_name].split():
                yield node.tag, u'[@{}={}]'.format(attr_name, val)


def minhash(string_set):
    hashers = [xxhash.xxh32(w.encode('utf8')) for w in string_set]
    hashes = np.asarray([h.intdigest() for h in hashers])
    while True:
        hashes *= 2654435761
        hashes %= 2 ** 32
        yield np.min(hashes)


def minhash_slower_but_randomer(string_set):
    hashers = [xxhash.xxh32(w.encode('utf8')) for w in string_set]
    while True:
        yield min(h.intdigest() for h in hashers)
        for h in hashers:
            h.update('.')


def sketch_doc(doc, n_hashes=100):
    if isinstance(doc, (str, unicode)):
        doc = re.sub('(?i)^([^>]*) encoding=[^> ]*', r'\1', doc)
        doc = etree.fromstring(doc, parser=etree.HTMLParser())
    paths = ('/'.join(path) for path in set(extract_paths(doc)))
###    out = np.empty(n_hashes, dtype='i4')
###    out[:] = itertools.islice(minhash(paths), n_hashes)
    return array.array('i', itertools.islice(minhash(paths), n_hashes))


def sketch_docs(docs, n_jobs=1, n_hashes=50):
    return Parallel(n_jobs=n_jobs)(delayed(sketch_doc)(doc, n_hashes=n_hashes)
                                   for doc in docs)
