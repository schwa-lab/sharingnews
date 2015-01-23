# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations
import likeable.models_helpers


class Migration(migrations.Migration):

    dependencies = [
        ('likeable', '0015_downloadedarticle_structure_sketch'),
    ]

    operations = [
        migrations.AddField(
            model_name='downloadedarticle',
            name='structure_group',
            field=models.IntegerField(null=True),
            preserve_default=True,
        ),
        migrations.AlterField(
            model_name='downloadedarticle',
            name='structure_sketch',
            field=likeable.models_helpers.IntArrayField(null=True, db_index=True),
            preserve_default=True,
        ),
    ]
