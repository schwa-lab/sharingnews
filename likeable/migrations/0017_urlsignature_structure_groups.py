# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('likeable', '0016_auto_20150121_0301'),
    ]

    operations = [
        migrations.AddField(
            model_name='urlsignature',
            name='structure_groups',
            field=models.CommaSeparatedIntegerField(max_length=15, null=True),
            preserve_default=True,
        ),
    ]
