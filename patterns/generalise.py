from scrapy.selector import Selector

# find coverage loss examples

# take html file paths as input
# for each file, apply selector and report coverage

import sys

def apply_selector(contents, pattern):
	return Selector(text=contents).css(pattern).extract()

matched = 0
total = 0

from statread import replace_extension, statuses

selector = sys.argv[1]
for fn in sys.stdin:
	fn = fn.rstrip()
	fn = fn.strip('"')
	with file(fn) as f:
		stat_fn = replace_extension(fn, 'stat')
		stats = list(statuses(file(stat_fn).readlines()))

		contents = f.read()
		result = apply_selector(contents, selector)
		print stats[-1].url
		print result
		print
		if result:
			matched += 1
		total += 1

print 'cov: %d/%d = %5.2f%%' % (matched, total, matched/float(total)*100.0)