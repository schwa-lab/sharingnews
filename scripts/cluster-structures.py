#!/usr/bin/env python
from __future__ import print_function, division

import time
import base64
import os
import argparse
import datetime
import gc

import django
import scipy.spatial.distance
from django.db.models import Count
from sklearn.metrics import pairwise_distances
from sklearn.metrics import silhouette_score
from sklearn.cluster import dbscan
from sklearn.externals import joblib
import numpy as np

from likeable.models import DownloadedArticle

django.setup()

ap = argparse.ArgumentParser()
ap.add_argument('--eps', type=float, default=0.3)
ap.add_argument('--min-samples', type=float, default=20)
ap.add_argument('--max-sketches', type=int, default=20000)
ap.add_argument('--memory-path', default='/data1/joel-tmp')
ap.add_argument('--out-path', default='~likeable/data/structure_sketch/{}.jl')
ap.add_argument('--n-jobs', type=int, default=1)
ap.add_argument('domains', nargs='+')
args = ap.parse_args()

mem = joblib.Memory(args.memory_path, verbose=0)


def process_domain(domain):
    print('Fetching for', domain)
    start = time.time()
    qs = DownloadedArticle.objects.filter(article__url_signature__base_domain=domain).filter(structure_sketch__isnull=False).values('structure_sketch').annotate(n=Count('pk')).values_list('structure_sketch', 'n')
    if args.max_sketches > 0:
        qs = qs.order_by('-n')[:args.max_sketches]
    sketches, weights = zip(*qs)
    weights = np.array(weights)
    #print('Largest weight', np.max(weights), 'at', np.argmax(weights))
    print('Fetched', len(sketches), 'sketches for', np.sum(weights), 'articles at', domain, 'in', time.time() - start, 'seconds')
    sketch_array = np.fromstring(''.join(base64.b64decode(s) for s in sketches), dtype='>u4').reshape(-1, 100)
    start = time.time()
    if len(sketch_array) < 50000:
        dist = mem.cache(pairwise_distances)(sketch_array, metric='hamming', n_jobs=args.n_jobs)
        print('Calculated pairwise distances for', domain, 'in', time.time() - start, 'seconds')
        off_diagonal = scipy.spatial.distance.squareform(dist, checks=False)
        print('min=', off_diagonal.min(), 'median=', np.median(off_diagonal), 'max=', off_diagonal.max(), 'mean=', np.mean(off_diagonal))
        del off_diagonal
        start = time.time()
        cores, labels = mem.cache(dbscan)(dist, eps=args.eps, min_samples=args.min_samples, sample_weight=weights, metric='precomputed')
    else:
        dist = None
        print('Not enough memory? Avoiding distance precomputation')
        start = time.time()
        cores, labels = mem.cache(dbscan)(sketch_array, eps=args.eps, min_samples=args.min_samples, sample_weight=weights, metric='hamming')
    print('Clustered', domain, 'in', time.time() - start, 'seconds')

    labelled_mask = labels != -1
    n_labelled = np.sum(weights[labelled_mask])
    proba = np.bincount(np.unique(labels, return_inverse=True)[1], weights=weights) / np.sum(weights)
    n_clusters = len(np.unique(labels[labelled_mask]))
    if labelled_mask.sum() == 0:
        print('All noise :(((((')
        silhouette = -np.inf
    elif n_clusters < 2:
        print('Too few clusters for silhouette')
        silhouette = -np.inf
    elif dist is None:
        print('Require full dist matrix for silhouette')
        silhouette = np.nan
    else:
        try:
            subset = np.compress(labelled_mask, dist, axis=1)
            subset = np.compress(labelled_mask, subset, axis=0, out=subset[:subset.shape[1]])
            silhouette = silhouette_score(subset, labels[labelled_mask], sample_weight=weights[labelled_mask], metric='precomputed')
            del subset
        except MemoryError:
            print('MemoryError in silhouette calculation')
            silhouette = 0
    entropy = -np.sum(proba * np.log(proba))
    inlier_pct = n_labelled * 100. / np.sum(weights)
    print('Produced', n_clusters, 'clusters with', '{:0.1f}'.format(inlier_pct), '% inliers, with silhouette', '{:0.3f}'.format(silhouette), ', and entropy', '{:0.3f}'.format(entropy))
    path = os.path.expanduser(args.out_path.format(domain))
    joblib.dump({'sketches': sketches,
                 'weights': weights,
                 #'dist': dist,
                 'cores': cores,
                 'labels': labels,
                 'silhouette': silhouette,
                 'entropy': entropy,
                 'inlier_pct': inlier_pct,
                 'n_clusters': n_clusters,
                 'args': args,
                 'when': datetime.datetime.now()},
                path)
    print('Wrote to', path)
    print()

for domain in args.domains:
    process_domain(domain)
    gc.collect()
