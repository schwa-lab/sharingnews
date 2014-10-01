# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('likeable', '0007_auto_20140918_1443'),
    ]

    operations = [
        migrations.AddField(
            model_name='downloadedarticle',
            name='canonical_url',
            field=models.TextField(null=True),
            preserve_default=True,
        ),
        migrations.AddField(
            model_name='downloadedarticle',
            name='fetch_when',
            field=models.DateTimeField(null=True),
            preserve_default=True,
        ),
    ]
