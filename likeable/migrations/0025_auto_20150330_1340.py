# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('likeable', '0024_auto_20150330_1339'),
    ]

    operations = [
        migrations.AlterField(
            model_name='downloadedarticle',
            name='canonical_url',
            field=models.TextField(null=True, db_index=True),
        ),
    ]
