# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('likeable', '0011_auto_20141106_1148'),
    ]

    operations = [
        migrations.AlterField(
            model_name='article',
            name='total_shares',
            field=models.PositiveIntegerField(null=True),
        ),
        migrations.AlterIndexTogether(
            name='article',
            index_together=set([('fetch_status', 'url_signature'), ('url_signature', 'fb_created'), ('total_shares', 'url_signature')]),
        ),
    ]
