import csv
from collections import namedtuple, defaultdict
SiteInfo = namedtuple('SiteInfo', 'name domain body title author date')

def read_csv(fn):
	return csv.reader(file(fn))

def parse_csv(fn, field_names):
	rows = read_csv(fn)

	# site -> { field -> [pattern] }
	for row in rows:
		info = SiteInfo(*row[:6])
		yield info

def selectors_by_site(infos):
	site_to_selectors = defaultdict(lambda: defaultdict(list))

	for info in infos:
		domain = info.domain
		for field in 'body title author date'.split():
			selector = getattr(info, field)
			if selector:
				site_to_selectors[domain][field].append(selector)

	return site_to_selectors

def selectors_by_field(infos):
	selectors = defaultdict(set)
	for info in infos:
		for field in 'body title author date'.split():
			selector = getattr(info, field)
			if selector:
				selectors[field].add(selector)
	return selectors

if __name__ == '__main__':
	import sys
	infos = parse_csv(sys.argv[1], [])
	sels = selectors_by_field(infos)
	print sels
