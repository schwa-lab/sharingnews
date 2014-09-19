# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('likeable', '0005_auto_20140916_0407'),
    ]

    operations = [
        migrations.AddField(
            model_name='article',
            name='fetch_status',
            field=models.IntegerField(null=True),
            preserve_default=True,
        ),
        migrations.AddField(
            model_name='downloadedarticle',
            name='fields_dirty',
            field=models.BooleanField(default=True),
            preserve_default=True,
        ),
    ]
