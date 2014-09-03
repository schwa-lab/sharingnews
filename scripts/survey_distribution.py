from __future__ import print_function, division
from collections import Counter, defaultdict
import operator

from likeable_scrapy.cleaning import strip_subdomains

MONTH_FIELD = 1


def get_status_binary(l):
    status = l[8]
    if status == '200':
        return True
    else:
        return False


def get_status_group(l):
    status = l[8]
    if status.startswith('<') or status == '-':
        return 'ERR'
    elif status == '200?':
        return 'HOME'
    else:
        return status[0] + 'xx'


def _norm_date(dt, n_months):
    if n_months is None:
        return
    return (dt[:4] + '-' +
            '%02d' % ((int(dt[5:7]) - 1) // n_months * n_months + 1))


def get_distribs(key_field, get_cat, n_months, weight=None):
# Group survey by status (cat), sig (key) and date group
    distrs = defaultdict(Counter)
    for l in open('data/sample-survey-v2'):
        l = l.rstrip('\r\n').split('\t')
        dt = _norm_date(l[MONTH_FIELD], n_months)
        distrs[l[key_field], dt][get_cat(l)] += 1

    if weight is None:
        get_weight = lambda k: 1
    else:
        get_weight = weight.get

    for k in distrs:
        distr = distrs[k]
        w = get_weight(k) or 0  # HACK due to dirty data?
        total = sum(distr.values())
        distrs[k] = {c: w * n / total
                     for c, n in distr.items()}
    return distrs


def get_sig_weights(n_months):
    # Get overall frequency for each key and date
    sig_weight = defaultdict(int)
    for l in open('data/url-sig-frequencies.txt'):
        l = l.rstrip('\r\n').split('\t')
        try:
            sig_weight[l[2], _norm_date(l[1], n_months)] += int(l[0])
        except (IndexError, ValueError):
            # Dirty data
            pass
    sig_weight.default_factory = None
    return sig_weight


def _sig_to_domain(sig):
    return strip_subdomains(sig.split('/')[0])


def regroup_by_domain(distrs):
    out = defaultdict(lambda: defaultdict(float))
    for (k, m), distr in distrs.iteritems():
        for c, n in distr.iteritems():
            out[_sig_to_domain(k), m][c] += n
    return out


def get_all_cats(distrs):
    cats = set()
    for distr in distrs.itervalues():
        for c in distr:
            cats.add(c)
    return sorted(cats)


if __name__ == '__main__':
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument('-m', '--month-quant', type=int,
                    help='Group this many months together (default, all time)')
    ap.add_argument('--by-sig', default=False, action='store_true')
    ap.add_argument('--use-end-sig', default=False, action='store_true',
                    help='Calculates status on the basis of likely canonical '
                         'URL signature')
    cat_opts = {
        'status-binary': get_status_binary,
        'status-group': get_status_group,
    }
    ap.add_argument('-c', '--cats', choices=cat_opts.keys(),
                    default='status-binary')
    args = ap.parse_args()

    n_months = getattr(args, 'month_quant', None)
    if n_months is not None and 12 % n_months != 0:
        ap.error('--month-quant (-m) must divide into 12')

    sig_weight = get_sig_weights(n_months)
    key_field = 4  # start sig
    if args.use_end_sig:
        tmp = get_distribs(key_field, operator.itemgetter(7), n_months,
                           weight=sig_weight)
        sig_weight = defaultdict(float)
        for (start_sig, mo), distr in tmp.iteritems():
            for end_sig, n in distr.iteritems():
                sig_weight[end_sig, mo] += n
        key_field = 7  # end sig
    distrs = get_distribs(key_field, cat_opts[args.cats], n_months,
                          weight=sig_weight)
    if not args.by_sig:
        distrs = regroup_by_domain(distrs)

    # output
    all_cats = get_all_cats(distrs)
    print('key', 'month', *all_cats, sep='\t')
    for k, v in sorted(distrs.iteritems()):
        k = list(k)
        k.extend(v.get(c, 0) for c in all_cats)
        print(*k, sep='\t')
