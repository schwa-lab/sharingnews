from __future__ import print_function
from collections import defaultdict
import sys
results = defaultdict(list)
for l in sys.stdin:
    i, ngram, freq = l.strip().split('\t')[:3]
    ngram = tuple(ngram.split())
    for j in range(len(ngram)):
        frame = ngram[:j] + ('*',) + ngram[j+1:]
        results[frame].append((i, ' '.join(ngram), freq))

results = [tup for tup in results.iteritems() if len(tup[-1]) > 1]
results.sort(key=lambda tup: (-len(tup[-1]), tup[0]))
for i, (frame, ngrams) in enumerate(results):
    frame = ' '.join(frame)
    j = i + 1
    print(j, frame, '-----', len(ngrams), sum(int(ngram[-1]) for ngram in ngrams), sep='\t')
    for ngram in ngrams:
        print(j, frame, *ngram, sep='\t')
