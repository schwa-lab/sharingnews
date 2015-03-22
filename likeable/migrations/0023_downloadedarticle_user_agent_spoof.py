# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('likeable', '0022b_20150311_0213'),
    ]

    operations = [
        migrations.AddField(
            model_name='downloadedarticle',
            name='user_agent_spoof',
            field=models.CharField(max_length=10, null=True),
        ),
    ]
