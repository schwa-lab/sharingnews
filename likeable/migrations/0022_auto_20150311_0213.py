# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations
import likeable.models


class Migration(migrations.Migration):

    dependencies = [
        ('likeable', '0021_auto_20150309_1330'),
    ]

    operations = [
        migrations.AddField(
            model_name='article',
            name='rand',
            field=models.FloatField(default=likeable.models._random, help_text=b'Random number reproducable/fast random ordering'),
        ),
    ]
