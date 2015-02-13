from __future__ import print_function
import sys
def _(s, quote=True):
    s = s.replace('&', '&amp;').replace('>', '&gt;').replace('<', '&lt;')
    if quote:
        s.replace('"', '&quot;')
    return s
field_breaks = [0, 8, 13, 21, 46, None]
slices = [slice(start, stop) for start, stop in zip(field_breaks, field_breaks[1:])]
sid = 1
tcount = 0
for l in sys.stdin:
    para, tid, pos, norm, sem = [l[sl].strip() for sl in slices]
    if pos.startswith('-'):
        sid += 1
        tcount = 0
        print()
        continue
    tcount += 1
    pos = _(pos)
    norm = _(norm, quote=False)
    sem = _(sem.partition(' ')[0])
    print('<w id="{sid}.{tcount}" pos="{pos}" sem="{sem}">{norm}</w>'.format(**locals()), end=' ')
    psid = sid
print()
