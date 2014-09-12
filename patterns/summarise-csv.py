#! /usr/bin/env python

from collections import defaultdict
# site -> { body:,date:,title:,author: }
groups = defaultdict(dict)

import sys
fn = sys.argv[1]

fields = ['body', 'date', 'title', 'author', 'count']

import csv
with file(fn) as f:
    for row in csv.reader(f):
        groups[row[0].replace('../html-sample/', '')][row[1]] = float(row[2])/float(row[3])
        if row[1] == 'body':
            groups[row[0].replace('../html-sample/', '')]['count'] = row[3]
        #writer.writerow([row[0].replace('../html-sample/', ''), row[1], float(row[2])/float(row[3])])

#print groups
writer = csv.writer(sys.stdout)
for site, info in groups.items():
    # print site, info
    writer.writerow([site] + [info.get(f, 0) for f in fields])
