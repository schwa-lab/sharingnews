from __future__ import print_function, division
import csv
import sys
import itertools
import operator
import math
import re
import os
from xml.sax.saxutils import escape as xml_escape
from likeable.models import FINE_HISTOGRAM_BINS

OUT_DIR = 'histogram-html'

WIDTH = 25  # cm
LEQ = '\xe2\x89\xa4'
N_TICKS = 6
TICK_WIDTH = WIDTH / (N_TICKS - 1)

reader = csv.reader(sys.stdin)
print(next(reader), file=sys.stderr)  # discard header
reader = sorted((row[0], int(row[1]), int(row[2]), int(row[3]), row[4], row[5]) for row in reader)

def share_range(group):
    if group == 0:
        return -1, 0
    min_shares = int(math.floor(FINE_HISTOGRAM_BINS[group - 1]))
    max_shares = int(math.floor(FINE_HISTOGRAM_BINS[group]))
    return min_shares, max_shares

def group_label(g):
    _, s = share_range(g)
    s = str(s)
    if s == '1' and g > 1:
        return '&nbsp;'
    if not re.match('^10*$|^0$', s):
        return '&nbsp;'
    if s.endswith('000000'):
        return s[:-6] + 'M'
    if s.endswith('000'):
        return s[:-3] + 'K'
    return s

def draw_ticks(max_cnt, fdomain):
    # Ticks
    print('<tr><th></th><td class="xticks">', file=fdomain)
    for i in range(N_TICKS):
        freq = int(max_cnt / (N_TICKS - 1) * i)
        print('<span style="width: {}cm">{}</span>'.format(TICK_WIDTH, freq), file=fdomain, end='')
    print('<tr><th></th><td>', file=fdomain)

with open(os.path.join(OUT_DIR, 'style.css'), 'w') as fstyle:
    print('table {border-collapse: collapse}', file=fstyle)
    print('tr, td, th {margin: 0; padding: 0; border: 0; }', file=fstyle)
    print('.hist .xticks span { border: none ; border-left: 1px solid black; font-size: .5cm }', file=fstyle)
    print('.hist thead {border-bottom: 1px solid}', file=fstyle)
    print('.hist tfoot {border-top: 1px solid}', file=fstyle)
    print('#twlegend {border: 1px solid black} ', file=fstyle)
    print('.hist, #twlegend {font-size: .2cm} ', file=fstyle)
    print('.hist thead th {font-size: .4cm; text-align: center} ', file=fstyle)
    print('.hist th {text-align: right} ', file=fstyle)
    print('#twlegend td {text-align: center} ', file=fstyle)
    print('.hist tr span { border: 1px solid black; white-space: nowrap }', file=fstyle)
    print('.hist tr span, .hist tr span > a { display: inline-block; text-decoration: none; }', file=fstyle)
    print('.hist tr span > a:hover { background: blue }', file=fstyle)
    print('#indexlisting > li { float: left; width: 15em }', file=fstyle)
    N_FB_GROUPS = max(g for _, g, _, _, _, _ in reader) + 1
    N_TW_GROUPS = max(g for _, _, g, _, _, _ in reader) + 1
    for i in range(N_FB_GROUPS):
        print('.fb{} {{ background: rgba(0, 0, 255, {}); }}'.format(i, i / N_FB_GROUPS), file=fstyle)
    for i in range(N_TW_GROUPS):
        print('.tw{} {{ background: rgba(255, 0, 0, {}); }}'.format(i, i / N_TW_GROUPS), file=fstyle)
    print('.tooltip-inner { white-space: normal;}', file=fstyle)

findex = open(os.path.join(OUT_DIR, 'index.html'), 'w')
header = []
header.append('''
<link rel="stylesheet" href="https://maxcdn.bootstrapcdn.com/bootstrap/3.3.2/css/bootstrap.min.css">

<!-- Optional theme -->
<link rel="stylesheet" href="https://maxcdn.bootstrapcdn.com/bootstrap/3.3.2/css/bootstrap-theme.min.css">

<!-- Latest compiled and minified JavaScript -->
<script src="https://code.jquery.com/jquery-1.11.2.min.js"></script>
<script src="https://maxcdn.bootstrapcdn.com/bootstrap/3.3.2/js/bootstrap.min.js"></script>
              ''')
header.append('<meta http-equiv="Content-Type" content="text/html; charset=utf-8">')
header.append('<link href="style.css" rel="stylesheet">')
print('\n'.join(header), file=findex)  # partial header for index
header.append('<ol class="breadcrumb"><li><a href="index.html">Home</a></li></ol>')
header.append('<table id="twlegend" style="position: fixed; right: 2em; top: 1em">')
header.append('<thead><tr><th>Tweets</th></tr></thead>')
for i in range(N_TW_GROUPS):
    header.append('<tr class="tw{}"><td>{}</td></tr>'.format(i, group_label(i)))
header.append('</table>')

print('<body>', file=findex)
print('<h1>Likeable Engine share count histograms</h1>', file=findex)
print('<p class="pull-left bg-info" style="width: 15em; margin: 1.45em; padding: .5em; box-shadow: 0 1px 3px rgba(0,0,0,.25)">These interactive histograms show the distribution of Facebook and Twitter share counts among articles tracked by the <a href="http://likeable.share-wars.com">Likeable Engine</a> in the first half of 2014. Articles more shared on Twitter are more red in the histogram. Click a section of a histogram to see an example article.</p>', file=findex)
print('<ul id="indexlisting">', file=findex)

for domain, tuples in itertools.groupby(sorted(reader), operator.itemgetter(0)):
    tuples = list(tuples)
    total = sum(freq for _, fb_group, _, freq, _, _ in tuples if fb_group > 0)
    if total < 2000:
        continue
    print('<li><a href="{domain}.html">{domain}</a></li>'.format(domain=domain), file=findex)
    fdomain = open(os.path.join(OUT_DIR, domain + '.html'), 'w')
    print('\n'.join(header), file=fdomain)
    max_cnt = max(sum(freq for _, _, _, freq, _, _ in fb_tuples if fb_group > 0) for fb_group, fb_tuples in itertools.groupby(tuples, operator.itemgetter(1)))
    print(domain, total, max_cnt, max(fb_group for _, fb_group, _, _, _, _ in tuples), file=sys.stderr)
    print('<h1><a href="http://{0}">{0}</a> share count histogram</h1>'.format(domain), file=fdomain)
    print('<table class="hist">', file=fdomain)

    print('<thead><tr><th></th><th>Number of URLs</th></tr>', file=fdomain)
    draw_ticks(max_cnt, fdomain)
    print('</thead>', file=fdomain)

    prev = -1
    for fb_group, fb_tuples in itertools.groupby(tuples, operator.itemgetter(1)):
        for i in range(prev + 1, fb_group):
            print('<tr><th>{}</th></tr>'.format(group_label(i)), file=fdomain)
        fb_min, fb_max = share_range(fb_group)
        row_parts = []
        row_parts.append('<tr><th>{0}</th><td><span class="xfb{1}">'.format(group_label(fb_group), fb_group))
        for _, _, tw_group, freq, ex_title, ex_url in fb_tuples:
            tw_min, tw_max = share_range(tw_group)
            title_text = "{fb_min}&lt;fb{LEQ}{fb_max} and {tw_min}&lt;tw{LEQ}{tw_max}:<br>{freq} items such as <br><em>{ex_title}</em>".format(**locals())
            row_parts.append('<a class="tw{}" style="width:{}cm" title="{}" href="{}" target="_blank">&nbsp;</a>'.format(tw_group, freq * WIDTH / max_cnt, xml_escape(title_text), xml_escape(ex_url)))
        row_parts.append('</span></td></tr>')
        print(''.join(row_parts), file=fdomain)  # avoid space between spans
        prev = fb_group

    print('<tfoot>', file=fdomain)
    draw_ticks(max_cnt, fdomain)
    print('</tfoot>', file=fdomain)
    print('</table>', file=fdomain)
    print('<script>$(window).load(function() {$(".hist tr span > a").tooltip({html: true});});</script>', file=fdomain)
    fdomain.close()

print('</ul></body>', file=findex)
findex.close()
