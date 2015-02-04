from __future__ import print_function
import sys
import os
import re
from collections import defaultdict
import random

results = defaultdict(list)

for path in sys.argv[1:]:
    xml = open(path).read().replace('&#13;', '')
    for match in re.finditer('<EVENT.*?>', xml):
        pre = ' '.join(re.sub('<.*?>', '', xml[:match.start()]).split('\n')[-1].split()[-5:])
        post = ' '.join(re.sub('<.*?>', '', xml[match.end():]).split('\n')[0].split()[:6])
        attrs = [attr.split('=')[1].strip('"') for attr in match.group()[:-1].split()[2:]]
        results[tuple(attrs)].append((pre + ' **' + post, os.path.basename(path)))

print('Frequency\tEvent class\tTense\tAspect\tPolarity\tModality\tExample\tExample doc')
for attrs, examples in sorted(results.items(), key=lambda tup: -len(tup[1])):
    print(len(examples), *(attrs + tuple(random.choice(examples))), sep='\t')
