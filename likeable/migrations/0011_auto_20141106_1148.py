# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('likeable', '0010_auto_20141013_0526'),
    ]

    operations = [
        migrations.AlterField(
            model_name='article',
            name='total_shares',
            field=models.PositiveIntegerField(null=True, db_index=True),
        ),
    ]
