#!/usr/bin/env python
# Download Likeable Engine weekly delta from dropbox
from __future__ import print_function
import datetime
import os
import shutil
import sys

import dropbox

from likeable import secret

OUT_ROOT = sys.argv[1]

sess = dropbox.session.DropboxSession(secret.DELTA_DROPBOX_APP_KEY, secret.DELTA_DROPBOX_APP_SECRET)
assert secret.DELTA_DROPBOX_ACCESS_TOKEN.startswith('oauth1:')
sess.set_token(*secret.DELTA_DROPBOX_ACCESS_TOKEN.split(':')[1:])
cl = dropbox.client.DropboxClient(sess)

now = datetime.datetime.utcnow()

out_dir = None
for path in ['/linkage_delta/WEEKLYDELTA_statistic.summary.txt', '/linkage_delta/WEEKLYDELTA_article.report.txt', '/linkage_delta/sites.txt']:
    meta = cl.metadata(path)
    modified = datetime.datetime.strptime(meta['modified'], "%a, %d %b %Y %H:%M:%S +0000")
    if out_dir is None:
        out_dir = os.path.join(OUT_ROOT, modified.strftime('%Y-%m-%d'))
        os.mkdir(out_dir)
    assert (now - modified).days < 5 and (now - modified) > datetime.timedelta(), '{} not modified in last 5 days'.format(path)
    assert 100 < meta['bytes'], '{} is too small (< 100B)'.format(path)
    assert 1024 * 1024 * 300 > meta['bytes'], '{} is too big (> 300MB)'.format(path)
    with cl.get_file(path) as fsrc:
        with open(os.path.join(out_dir, os.path.basename(path)), 'wb') as fdst:
            shutil.copyfileobj(fsrc, fdst)

print(out_dir)
