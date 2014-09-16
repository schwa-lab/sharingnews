import ujson as json

import glob
import os
import sys
import csv

key = sys.argv[1]
site = sys.argv[2]

out = csv.writer(sys.stdout)
for json_fn in glob.glob('../html-sample/{}/*.json'.format(site)):
    if not os.path.isfile(json_fn): continue

    extracted = json.load(file(json_fn))
    out.writerow([ extracted['filename'], extracted.get(key, '').encode('u8') ])

