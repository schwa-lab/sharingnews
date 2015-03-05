#!/usr/bin/env python
"""

REQUIRES STATISTICS TO BE SORTED BY TIME

It's easier to ingest from one datasource, so we join article summary and statistics.

Reasonable to do at small scale. May be intractable at large scale.
Might be worth writing in C++
"""

from collections import defaultdict
import argparse
import datetime
strptime = datetime.datetime.strptime

DELTAS = [
    (datetime.timedelta(), 'initial'),
    (datetime.timedelta(seconds=60 * 30), '30m'),
    (datetime.timedelta(seconds=60 * 60 * 1), '1h'),
    (datetime.timedelta(seconds=60 * 60 * 2), '2h'),
    (datetime.timedelta(seconds=60 * 60 * 6), '6h'),
    (datetime.timedelta(seconds=24 * 60 * 60), '1d'),
    (datetime.timedelta(seconds=24 * 60 * 60 * 5), '5d'),
]

TOL = datetime.timedelta(seconds=5 * 60)

TOL_DELTAS = [(d + TOL, n) for d, n in DELTAS]


def parse_iso_time(time):
    if '.' not in time:
        time += '.000'
    return strptime(time, "%Y-%m-%dT%H:%M:%S.%f")

def join(articles, statistics):
    grouped_stats = defaultdict(list)
    stat_header = statistics.next().rstrip()
    assert stat_header.startswith('article_Id|')
    stat_header = stat_header.split('|')
    stat_dt_field = stat_header.index('statistic_Date') - 1
    assert stat_header[-1] == 'statistic_Tweets'
    assert stat_header[-2] == 'statistic_FbTotal'
    for l in statistics:
        art_id, _, stats = l.partition('|')
        grouped_stats[art_id].append(stats)

    art_header = articles.next()
    assert art_header.startswith('article_Id|')
    id_field = art_header.rstrip().split('|').index('article_Id')
    url_field = art_header.rstrip().split('|').index('article_Url')
    site_field = art_header.rstrip().split('|').index('site_Id')
    base_dt_field = art_header.rstrip().split('|').index('article_Date')
    print('article_Id|site_Id|article_Url|article_Date|statistic_Json')
    for l in articles:
        l = l.rstrip()
        row = l.split('|')
        base_dt = parse_iso_time(row[base_dt_field])

        stats = TOL_DELTAS[:]
        for stat in grouped_stats[row[0]]:
            stat = stat.rstrip().split('|')
            stat_delta = parse_iso_time(stat[stat_dt_field]) - base_dt
            fb, tw = stat[-2:]
            stats.append((stat_delta, fb, tw))

        fb, tw = 0, 0
        stats.sort()
        out_stats = []
        for tup in stats:
            if len(tup) == 3:
                _, fb, tw = tup
            else:
                _, delta_name = tup
                out_stats.append('"{}":"{},{}"'.format(delta_name, fb, tw))

        print('%s|%s|%s|%s|{%s}' % (row[id_field], row[site_field], row[url_field],
                                    row[base_dt_field], ','.join(out_stats)))


if __name__ == '__main__':
    ap = argparse.ArgumentParser()
    ap.add_argument('articles', type=argparse.FileType('r'))
    ap.add_argument('statistics', type=argparse.FileType('r'))
    args = ap.parse_args()
    join(args.articles, args.statistics)
