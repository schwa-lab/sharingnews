# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('likeable', '0025_auto_20150330_1340'),
    ]

    operations = [
        migrations.CreateModel(
            name='BlacklistedUrl',
            fields=[
                ('url', models.URLField(max_length=256, serialize=False, primary_key=True)),
            ],
        ),
    ]
