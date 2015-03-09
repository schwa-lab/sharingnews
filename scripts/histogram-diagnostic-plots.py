from __future__ import print_function
import sys
import datetime
import codecs

import django
from django.db.models import F, Q
from sklearn.neighbors import KernelDensity
import matplotlib.pyplot as plt
import numpy as np
from pyqt_fit import kde, kde_methods
import peakdetect

from likeable.models import Article

django.setup()
now = datetime.datetime.now

MIN_SAMPLES = 1000
MAX_SAMPLES = 15000

def generate_datasets(domains, periods):
    conds = Q(fb_count_5d__gt=0) | Q(fb_count_longterm__gt=0, fb_count_longterm__gte=F('fb_count_5d')) | Q(tw_count_5d__gt=0)
    #conds = Q(fb_count_5d__isnull=False) | Q(fb_count_longterm__isnull=False, fb_count_longterm__gte=F('fb_count_5d')) | Q(tw_count_5d__isnull=False)
    for domain in domains:
        for start, stop in periods:
            # FIXME: should probably be using spider_when filter, but may be okay where requiring >0 shares
            articles = Article.objects.filter(conds, fb_created__gte=start, fb_created__lt=stop).close_scrapes()
            if domain:
                articles = articles.for_base_domain(domain)
            data = articles.values_list('fb_count_5d', 'fb_count_longterm', 'tw_count_5d').order_by('?')[:MAX_SAMPLES]
            data = [[c if c is not None else -1 for c in row] for row in data]
            if len(data) < MIN_SAMPLES:
                print('Skipping', domain, 'with', len(data), 'samples')
                continue
            data = np.transpose(data)
            yield articles, (domain, start, 'tw@5d'), data[2][data[2] > 0]
            yield articles, (domain, start, 'fb@5d'), data[0][data[0] > 0]
            yield articles, (domain, start, 'fb@longterm'), data[1][np.logical_and(data[1] > 0, data[1] >= data[0])]


class UTC(datetime.tzinfo):
    def utcoffset(self, dt):
        return datetime.timedelta(hours=0)
    def dst(self, dt):
        return None
    def tzname(self, dt):
         return "UTC"

html_out = open('histograms/index.html', 'w')
print('<html><style>img {width: 300px }</style>', file=html_out)
print('<table><thead><tr><th>Domain</th><th>TW@5d</th><th>FB@5d</th><th>FB@>1Mo</th></tr></thead><tbody>', file=html_out)
print(now(), 'Loading')
last_domain = None
MAY14 = (datetime.datetime(2014, 05, 01, tzinfo=UTC()), datetime.datetime(2014, 06, 01, tzinfo=UTC()))
HALF14 = (datetime.datetime(2014, 01, 01, tzinfo=UTC()), datetime.datetime(2014, 07, 01, tzinfo=UTC()))
Q2_14 = (datetime.datetime(2014, 04, 01, tzinfo=UTC()), datetime.datetime(2014, 07, 01, tzinfo=UTC()))
for articles, key, data in generate_datasets(sys.argv[1:], [HALF14]):
    domain = key[0]
    name = '{0}-{1:%Y%m}-{2}'.format(*key)
    if last_domain != domain:
        if last_domain is not None:
            print('</tr>', file=html_out)
        print('<tr><td>{}</td>'.format(domain), file=html_out)

    print(now(), 'Got', name, 'of shape', data.shape)
    if data.shape[0] < 1000:
        print('<td>{} samples</td>'.format(data.shape[0]), file=html_out)
        continue
    log_data = np.log10(data)
    xmax = log_data.max()
    plt.figure()
    plt.hist(log_data, bins=50, fc='#AAAAFF', normed=True)
    X_plot = np.linspace(0, xmax, MIN_SAMPLES)
###    for (k, b, c) in [('gaussian', .4, '#ff0000')]: #, ('tophat', .7, '#0000ff')]:
        #kde = KernelDensity(kernel=k, bandwidth=b).fit(np.hstack([log_data, np.zeros(2 * np.sum(log_data == 0))])[:, None])
        #y = np.exp(kde.score_samples(X_plot[:, None]))

    y = kde.KDE1D(log_data, lower=0,
                  method=kde_methods.linear_combination,
                  covariance=kde.scotts_covariance)(X_plot)
    plt.plot(X_plot, y, color='red')
    maxima, minima = peakdetect.peakdetect(y, X_plot, lookahead=len(X_plot)//100, delta=0)
    print('peakdetect:', 'maxima', maxima, 'minima', minima)
    for ext_x, ext_y in maxima + minima:
        plt.annotate('{:0.0f}'.format(10 ** ext_x), xy=(ext_x, ext_y), xytext=(ext_x + .01 * log_data.max(), ext_y + .1 * y.max()),
                     arrowprops=dict(facecolor='black'))

    log_data.sort()
    plt.axvline(log_data[len(log_data) // 2], color='green')  # ~median
    plt.axvline(log_data[len(log_data) // 4], color='green', ls='-.')  # 1Q
    plt.axvline(log_data[3 * len(log_data) // 4], color='green', ls='-.')  # 3Q
    trimmed_data = log_data[:-len(log_data) // 20]  # drop top 5%
    trimmed_data = log_data[log_data > np.log10(2)]  # drop <= 2 shares
    trimmed_mean = trimmed_data.mean()
    def mean_and_sds(data, color):
        m = data.mean()
        s = data.std()
        plt.axvline(m, color=color)
        for i in range(1, 4):
            val = m + i * s
            if val < xmax:
                plt.axvline(val, color=color, ls='-.')
            val = m - i * s
            if val > 0:
                plt.axvline(val, color=color, ls='-.')

    mean_and_sds(log_data, 'blue')
    mean_and_sds(trimmed_data, 'orange')

    ltrimmed_data = log_data[log_data > np.log10(2)]
    plt.axvline(ltrimmed_data[len(ltrimmed_data) // 2], color='gray')  # ~median
    plt.axvline(ltrimmed_data[len(ltrimmed_data) // 4], color='gray', ls='-.')  # 1Q
    plt.axvline(ltrimmed_data[3 * len(ltrimmed_data) // 4], color='gray', ls='-.')  # 3Q

    path = 'histograms/{}.png'.format(name)
    plt.savefig(path)
    plt.close()
    print(now(), 'Wrote figure to', path)
    print('<td><a href="{0}.png"><img src="{0}.png"></a></td>'.format(name), file=html_out)
    last_domain = key[0]

    if 'fb@5d' not in name:
        continue
    N_SAMPLE = 50 if domain else 200
    sample_path = 'histograms/{}-sample.txt'.format(name)
    with codecs.open(sample_path, 'w', 'utf8') as sample_out:
        sample_points = [#(u'shared once', 1),
                         (u'25% above', 10 ** ltrimmed_data[len(ltrimmed_data) // 4]),
                         (u'75% above', 10 ** ltrimmed_data[-len(ltrimmed_data) // 4]),
                         (u'top 5%', 10 ** ltrimmed_data[-len(ltrimmed_data) // 20])]
        for sample_name, sample_start in sample_points:
            for tup in articles.close_scrapes().filter(fb_count_5d__gte=sample_start).values_list('fb_count_5d', 'id', 'title', 'fb_created', 'url').order_by('fb_count_5d', '?')[:N_SAMPLE]:
                print(sample_name, *tup, file=sample_out, sep=u'\t')
    from django.db import connection
    print(connection.queries[-1]['sql'])
    print(now(), 'Wrote sample to', sample_path)

print('</table><dl><dt>Blue</dt><dd>Mean and standard deviations</dd><dt>Green</dt><dd>Median and quartiles</dd><dt>Orange</dt><dd>Mean/SDs trimmed for >2 shares, < top 5%</dd><dt>Grey</dt><dd>Median and quartiles, trimmed for >2 shares</dd></dl></html>', file=html_out)
