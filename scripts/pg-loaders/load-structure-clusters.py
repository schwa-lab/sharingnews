#!/usr/bin/env python
from __future__ import print_function, division
import argparse
import os
import datetime

import django
from sklearn.externals import joblib
import numpy as np

from likeable.models import DownloadedArticle

now = datetime.datetime.now
django.setup()

ap = argparse.ArgumentParser()
ap.add_argument('joblib_dumps', nargs='+')
args = ap.parse_args()


for path in args.joblib_dumps:
    domain = os.path.basename(os.path.splitext(path)[0])
    print(now(), domain)
    cluster_data = joblib.load(path)
    labels = cluster_data['labels']
    mask = labels != -1
    label_weights = np.bincount(labels[mask], weights=cluster_data['weights'][mask])
    order = np.argsort(label_weights)[::-1]
    sketches = cluster_data['sketches']
    DownloadedArticle.objects.filter(article__url_signature__base_domain=domain, structure_group__isnull=False).update(structure_group=None)
    print(now(), 'Cleared former cluster annotations')
    for i, label in enumerate(order):
        label_inds = np.flatnonzero(labels == label)
        # b64-encoded
        label_sketches = [sketches[j] for j in label_inds]
        n_updates = DownloadedArticle.objects.filter(article__url_signature__base_domain=domain, structure_sketch__in=label_sketches).update(structure_group=i + 1)
        print(now(), 'Domain', domain, 'label', label, 'updated', n_updates, 'rows for', len(label_sketches), 'sketches')
