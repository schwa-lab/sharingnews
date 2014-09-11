# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('likeable', '0002_auto_20140911_0448'),
    ]

    operations = [
        migrations.AddField(
            model_name='urlsignature',
            name='body_html_selector',
            field=models.CharField(max_length=1000, null=True),
            preserve_default=True,
        ),
        migrations.AddField(
            model_name='urlsignature',
            name='byline_selector',
            field=models.CharField(max_length=1000, null=True),
            preserve_default=True,
        ),
        migrations.AddField(
            model_name='urlsignature',
            name='dateline_selector',
            field=models.CharField(max_length=1000, null=True),
            preserve_default=True,
        ),
        migrations.AddField(
            model_name='urlsignature',
            name='headline_selector',
            field=models.CharField(max_length=1000, null=True),
            preserve_default=True,
        ),
        migrations.AddField(
            model_name='urlsignature',
            name='media_selector',
            field=models.CharField(max_length=1000, null=True),
            preserve_default=True,
        ),
    ]
