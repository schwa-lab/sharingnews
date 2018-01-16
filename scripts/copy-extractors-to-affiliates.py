#!/usr/bin/env python
from __future__ import print_function
from collections import defaultdict

import django

from likeable.models import UrlSignature, EXTRACTED_FIELDS

django.setup()

AFFILIATE_GROUPS = [
    ('fairfax', ['smh.com.au', 'theage.com.au', 'brisbanetimes.com.au', 'canberratimes.com.au', 'watoday.com.au', 'brisbanetimes.com.au', 'dailylife.com.au', 'domain.com.au', 'drive.com.au',]),
    ('news au', ['couriermail.com.au', 'heraldsun.com.au', 'theaustralian.com.au', 'news.com.au', 'perthnow.com.au', 'adelaidenow.com.au', 'dailytelegraph.com.au',]),
    ('tribune', ['orlandosentinel.com','redeyechicago.com','chicagotribune.com','dailypress.com','sun-sentinel.com','baltimoresun.com','courant.com','mcall.com',]),
    ('medianews', ['dailybulletin.com', 'sgvtribune.com', 'dailybreeze.com', 'presstelegram.com', 'sbsun.com', 'pasadenastarnews.com',]),
    ('trinity mirror', ['mirror.co.uk', 'irishmirror.ie', 'dailyrecord.co.uk']),
    ('people', ['people.com', 'peoplestylewatch.com']),
    ('msn-anz', ['ninemsn.com.au', 'msn.co.nz']),
]

for name, domains in AFFILIATE_GROUPS:
    print('=== {} ==='.format(name))
    sigs = list(UrlSignature.objects.filter(base_domain__in=domains).domain_defaults().order_by('-modified_when'))
    all_agree = True
    for f in EXTRACTED_FIELDS:
        print(f)
        groups = defaultdict(list)
        for sig in sigs:
            sel = sig.get_selector(f)
            if sel.strip().startswith('<default>'):
                sel = '<default>'
            groups[sel].append(sig.base_domain)

        if len(groups) > 1:
            for sel, domains in sorted(groups.items(), key=lambda pair: len(pair[1])):
                print('  on {} domains: {}'.format(len(domains), domains))
                print('\n'.join('\t' + l for l in sel.split('\n')))
            all_agree = False
        else:
            print('  all agree'.format(f))

    if not all_agree:
        best = None
        for sig in sigs:
            if not all(sig.get_selector(f).startswith('<') for f in EXTRACTED_FIELDS):
                best = sig
                break
        if best is None:
            print("Something's gone wrong: couldn't find non-default sig")
            continue

        confirm = raw_input('Enter y to copy all from {}: '.format(best.base_domain))
        if confirm == 'y':
            for sig in sigs:
                for f in EXTRACTED_FIELDS:
                    sig.set_selector(f, best.get_selector(f))
                sig.save()
        else:
            print('Doing nothing')
