# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('likeable', '0017_urlsignature_structure_groups'),
    ]

    operations = [
        migrations.AddField(
            model_name='article',
            name='spider_when',
            field=models.DateTimeField(null=True),
        ),
    ]
