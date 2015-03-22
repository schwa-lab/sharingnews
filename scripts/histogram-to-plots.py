#!/usr/bin/env python

from __future__ import print_function, division
import math
import sys
import csv
from collections import defaultdict
import argparse
import os

import matplotlib.pyplot as plt

from likeable.models import FINE_HISTOGRAM_BINS

ap = argparse.ArgumentParser()
ap.add_argument('--min-samples', type=int, default=2000)
ap.add_argument('--in-file', type=argparse.FileType('r'), default=sys.stdin)
ap.add_argument('--title-fmt', default='{domain}')
ap.add_argument('--ext', default='pdf')
ap.add_argument('out_dir')
args = ap.parse_args()

reader = csv.DictReader(args.in_file)
by_domain = defaultdict(list)
for row in reader:
    by_domain[row['domain']].append(row)


def readable_number(n):
    # XXX: not fully-fledged
    n = int(n)
    d = len(str(n))
    if d > 6:
        return str(n)[:-6] + 'M'
    if d > 3:
        return str(n)[:-3] + 'K'
    return str(n)

idx = range(0, 68)
for domain, rows in by_domain.items():
    plt.clf()
    # TO[0] + DO: same ylim for fb and tw
    for service in ['fb', 'tw']:
        freq_dist = defaultdict(int)
        for row in rows:
            freq_dist[int(row[service + '@5d group'])] += int(row['frequency'])
        if sum(v for k, v in freq_dist.items() if k > 0) < args.min_samples:
            continue
        fig, ax = plt.subplots()
        ax.bar(idx, [freq_dist[i] for i in idx])
        ax.set_ylabel('Frequency'.format(freq_dist[0]))
        ax.set_xlabel('{} at 5 days'.format('Facebook shares' if service == 'fb' else 'Twitter shares'))
        ax.set_title(args.title_fmt.format(**locals()))
        xticks = idx[1::10]
        ax.set_xticks(xticks)
        ymax = max(v for k, v in freq_dist.items() if k > 0)
        if freq_dist[0] > ymax:
            ax.text(0, ymax * 1.05, freq_dist[0], ha='center')
        ax.set_ylim(0, ymax * 1.05)
        ax.set_xticklabels([readable_number(FINE_HISTOGRAM_BINS[i]) for i in xticks])
        path = '{}{}{}-{}.{}'.format(args.out_dir, os.path.sep, domain, service, args.ext)
        plt.savefig(path)
        print('wrote to ' + path)

    fig, ax = plt.subplots()
    freq_dist = defaultdict(int)
    for row in rows:
        freq_dist[int(row['fb@5d group']), int(row['tw@5d group'])] = int(row['frequency'])
    if sum(v for k, v in freq_dist.items() if k > 0) < args.min_samples:
        continue
    ax.imshow([[math.log(1 + freq_dist[i, j]) for i in idx[1:]] for j in idx[1:]],
              interpolation='nearest', cmap='Blues')
    ticks = idx[1::10]
    ax.set_title(args.title_fmt.format(**locals()))
    ax.set_xticks(ticks)
    ax.set_yticks(ticks)
    ax.set_xticklabels([readable_number(FINE_HISTOGRAM_BINS[i]) for i in xticks])
    ax.set_yticklabels([readable_number(FINE_HISTOGRAM_BINS[i]) for i in xticks])
    ax.set_xlabel('Facebook shares at 5 days')
    ax.set_ylabel('Twitter shares at 5 days')
    path = '{}{}{}-fb-vs-tw.{}'.format(args.out_dir, os.path.sep, domain, args.ext)
    fig.savefig(path)
    print('wrote to ' + path)
