# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('likeable', '0023_downloadedarticle_user_agent_spoof'),
    ]

    operations = [
        migrations.AlterField(
            model_name='urlsignature',
            name='body_text_selector',
            field=models.CharField(default=b'<default>((text))[property~="articleBody"] > p;\n((text))[itemprop~="articleBody"] > p;\n((text))((readability.summary))p', max_length=1000, null=True),
        ),
    ]
