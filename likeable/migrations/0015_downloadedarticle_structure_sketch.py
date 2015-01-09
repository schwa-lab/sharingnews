# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations
import likeable.models_helpers


class Migration(migrations.Migration):

    dependencies = [
        ('likeable', '0014_auto_20141208_0445'),
    ]

    operations = [
        migrations.AddField(
            model_name='downloadedarticle',
            name='structure_sketch',
            field=likeable.models_helpers.IntArrayField(null=True),
            preserve_default=True,
        ),
    ]
