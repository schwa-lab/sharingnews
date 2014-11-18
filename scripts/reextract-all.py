#!/usr/bin/env python
import django
django.setup()

from likeable.models import UrlSignature

print('NB: this does not run the enqueue cron or workers')

for sig in UrlSignature.objects.all().order_by('?'):
    sig.set_modified()
    sig.save()
