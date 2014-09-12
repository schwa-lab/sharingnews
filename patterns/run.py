#! /usr/bin/env python

import sys
html_dir = sys.argv[1]

import os
import glob

from bs4 import BeautifulSoup
import lxml.html
from lxml.cssselect import CSSSelector

from scrapy.selector import Selector

from gen import *

# site -> { field -> { extracted:, total: } }
from collections import defaultdict, Counter
coverage_per_site = defaultdict(lambda: defaultdict(lambda: defaultdict(int)))

infos = parse_csv(sys.argv[2], [])
infos = list(infos)
sels_by_field = selectors_by_field(infos)
sels_by_site = selectors_by_site(infos)

fields = ['body', 'title', 'author', 'date']

site_glob = '*' if len(sys.argv) < 4 else sys.argv[3]

def generate_jobs(basedir):
	for sitename in glob.glob(os.path.join(basedir, site_glob)):
		if not os.path.isdir(sitename): continue

		for cluster in glob.glob(os.path.join(sitename, '*.html')):
			if not os.path.isfile(cluster): continue

			yield dict(sitename=sitename, cluster=cluster)

from statread import should_ignore_page, replace_extension, statuses
import ujson as json

def normalise(text):
	return ' '.join(fragment.strip() for fragment in text)

import tldextract
def normalise_domain(cluster):
	stat_fn = replace_extension(cluster, 'stat')

	lines = file(stat_fn).readlines()
	stats = list(statuses(lines))

	if not stats: return None
	url = stats[-1].url

	result = tldextract.extract(url)
	if not result.suffix: return None
	return result.domain + '.' + result.suffix

def run_job(job_info):
	cluster = job_info['cluster']
	sitename = job_info['sitename']
	contents = file(cluster).read()

	results = []

	if should_ignore_page(cluster):
		return []

	extracted = {}
	for field in fields:
		normalised_domain = normalise_domain(cluster)
		if normalised_domain in sels_by_site:
			# print 'found', normalised_domain
			patterns = sels_by_site[normalised_domain]
		else:
			# print 'falling back', normalised_domain
			patterns = sels_by_field

		pattern_matched = False
		for pattern in patterns[field]:
			text = Selector(text=contents).css(pattern).extract()
			if text:
				results.append( (sitename, cluster, field, True, pattern) )
				extracted[field] = normalise(text)

				pattern_matched = True

				break

		if not pattern_matched:
			for pattern in sels_by_field[field]:
				text = Selector(text=contents).css(pattern).extract()
				if text:
					results.append( (sitename, cluster, field, True, pattern) )
					extracted[field] = normalise(text)

					pattern_matched = True

					break
		
		if not pattern_matched:
			results.append( (sitename, cluster, field, False, None) )

	extracted['filename'] = cluster

	with file(replace_extension(cluster, 'json'), 'w') as out:
		json.dump(extracted, out)

	return results

from multiprocessing import Pool
from multiprocessing.dummy import Pool as ThreadPool 
import signal

def init_worker():
    signal.signal(signal.SIGINT, signal.SIG_IGN)

pool = Pool(44, init_worker)

try:
	from itertools import islice
	#jobs = islice(generate_jobs('../html-sample'), 0, 1000)
	jobs = generate_jobs('../html-sample')
	results = pool.map(run_job, jobs)

	selectors_per_field_per_site = defaultdict(lambda: defaultdict(Counter))

	gathered = {}
	for result_bundle in results:
		for result in result_bundle:
			site, cluster, field, did_extract, selector = result
			if did_extract:
				coverage_per_site[site][field]['extracted'] += 1
				selectors_per_field_per_site[site][field][selector] += 1
			coverage_per_site[site][field]['total'] += 1

	import csv
	with file('out.csv', 'w') as out:
		writer = csv.writer(out) 
		for site, fields_and_counts in coverage_per_site.iteritems():
			for field, counts in fields_and_counts.iteritems():
				writer.writerow([site, field, counts['extracted'], counts['total']])

	with file('selectors.json', 'w') as out:
		json.dump(selectors_per_field_per_site, out)

except KeyboardInterrupt:
	print 'got ^C'
	pool.terminate()
	pool.join()

else:
	pool.close()
	pool.join()
