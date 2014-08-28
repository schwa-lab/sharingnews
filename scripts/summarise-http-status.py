"""
Put survey output on stdin
"""
from __future__ import print_function, division
from collections import defaultdict
import itertools
import operator
import sys

freq_by_month = defaultdict(int)

def read_grouped(f):
    while True:
        group = list(itertools.takewhile(lambda l: l.strip(), f))
        if not group:
            break
        yield group

stats = []
months = set()
total = 0
for group in read_grouped(sys.stdin):
    group_total = 0
    group_status = {}
    for l in group:
        l = l.rstrip('\n\r').split('\t')
        count = int(l[0])
        pat = tuple(l[1:4])
        month = l[4]
        end_url = l[7]
        status = l[9]
        mime = l[10]

        months.add(month)
        freq_by_month[month] += count
        group_total += count
        if not end_url:
            status = '.'
        if status == '200':
            status = '#'
        if status.startswith('4') or status.startswith('5') or status == '200?':
            status = 'x'
        if status.startswith('<'):
            status = '!'
        group_status[month] = status
    stats.append((l[6], group_total, group_status))
    total += group_total

months = sorted(months)

max_month = max(freq_by_month.values())
HIST_HEIGHT = 7
for cutoff in reversed(range(0, max_month + 1, max_month // HIST_HEIGHT)):
    print(''.join('*' if freq_by_month[month] >= cutoff else ' '
                  for month in months))
print()

for i in range(len(months[0])):
    chars = [m[i] for m in months]
    chars_norep = [cur if cur != prev else ' ' for prev, cur in zip([None] + chars, chars)]
    print(''.join(chars))
print()

stats.sort(key=operator.itemgetter(1), reverse=True)
cum_total = 0
for example_url, group_total, group_status in stats:
    cum_total += group_total
    if cum_total / total > 0.95:
        break
    print(''.join(group_status.get(m, ' ') for m in months),
          '%3.1f%%' % (100 * group_total / total),
          '%10d' % group_total,
          example_url,
          sep='\t')

