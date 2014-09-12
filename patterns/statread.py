import os

def replace_extension(fn, new_ext):
	filename, ext = os.path.splitext(fn)
	return filename + '.' + new_ext

from collections import namedtuple
Status = namedtuple('Status', 'code url mime')

def statuses(iter):
	for line in iter:
		line = line.rstrip()
		if line:
			bits = line.split('\t')
			if len(bits) == 3:
				yield Status(*bits)

def should_ignore_page(cluster_fn):
	stat_fn = replace_extension(cluster_fn, 'stat')

	lines = file(stat_fn).readlines()
	stats = list(statuses(lines))

	if not stats: return True
	return stats[-1].code != '200'