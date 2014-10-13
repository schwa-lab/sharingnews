# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('likeable', '0009_auto_20141003_0446'),
    ]

    operations = [
        migrations.AlterIndexTogether(
            name='article',
            index_together=set([('fetch_status', 'url_signature'), ('url_signature', 'fb_created')]),
        ),
    ]
