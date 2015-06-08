
# coding: utf-8

# In[15]:

urls = [l.strip().decode('utf-8').split('|')[2].split('/', 3)[-2:] for l in open('data/articleData.txt') if '|' in l and '//' in l]


# In[16]:

from collections import defaultdict
dd = defaultdict(set)
for domain, path in urls:
    dd[path].add(domain)


# In[18]:

import itertools
from collections import Counter
shared_path_counter = Counter()
for path, domains in dd.items():
    if len(domains) < 2:
        continue
    shared_path_counter.update(itertools.combinations(sorted(domains), 2))


# In[47]:

MIN_COUNT = 200
equivalence_classes = {}
for (domain1, domain2), count in shared_path_counter.items():
    if count < MIN_COUNT:
        continue
    cl1 = equivalence_classes.setdefault(domain1, set([domain1]))
    cl2 = equivalence_classes.setdefault(domain2, set([domain2]))
    if cl1 is not cl2:
        for domain_other in cl2:
            cl1.add(domain_other)
            equivalence_classes[domain_other] = cl1
            
distinct_equivalence_classes = {frozenset(cl) for cl in equivalence_classes.values()}


# In[48]:

for row in distinct_equivalence_classes:
    print(','.join(sorted(row)))


# In[ ]:



