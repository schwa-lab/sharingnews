# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('likeable', '0012_auto_20141106_1300'),
    ]

    operations = [
        migrations.AlterField(
            model_name='downloadedarticle',
            name='in_dev_sample',
            field=models.BooleanField(default=False, db_index=True),
        ),
        migrations.AlterField(
            model_name='urlsignature',
            name='body_html_selector',
            field=models.CharField(default=None, max_length=1000, null=True),
        ),
        migrations.AlterField(
            model_name='urlsignature',
            name='body_text_selector',
            field=models.CharField(default=b'<default>((text))((readability.summary))p', max_length=1000, null=True),
        ),
        migrations.AlterField(
            model_name='urlsignature',
            name='byline_selector',
            field=models.CharField(default=None, max_length=1000, null=True),
        ),
        migrations.AlterField(
            model_name='urlsignature',
            name='dateline_selector',
            field=models.CharField(default=b'<default>[property~=datePublished]::attr(datetime); [property~=dateCreated]::attr(datetime); [itemprop~=datePublished]::attr(datetime); [itemprop~=dateCreated]::attr(datetime)', max_length=1000, null=True),
        ),
        migrations.AlterField(
            model_name='urlsignature',
            name='headline_selector',
            field=models.CharField(default=b'<default>((text))[itemprop~="headline"]; ((text))h1; [property~="og:title"]::attr(content)', max_length=1000, null=True),
        ),
        migrations.AlterField(
            model_name='urlsignature',
            name='media_selector',
            field=models.CharField(default=None, max_length=1000, null=True),
        ),
    ]
