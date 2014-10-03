# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations
import likeable.models


class Migration(migrations.Migration):

    dependencies = [
        ('likeable', '0008_auto_20141001_1350'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='downloadedarticle',
            name='fields_dirty',
        ),
        migrations.AddField(
            model_name='downloadedarticle',
            name='body_text',
            field=models.TextField(null=True),
            preserve_default=True,
        ),
        migrations.AddField(
            model_name='downloadedarticle',
            name='scrape_when',
            field=models.DateTimeField(null=True),
            preserve_default=True,
        ),
        migrations.AddField(
            model_name='urlsignature',
            name='body_text_selector',
            field=models.CharField(max_length=1000, null=True),
            preserve_default=True,
        ),
        migrations.AddField(
            model_name='urlsignature',
            name='modified_when',
            field=models.DateTimeField(default=likeable.models.utcnow),
            preserve_default=True,
        ),
    ]
