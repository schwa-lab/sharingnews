# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('likeable', '0018_article_spider_when'),
    ]

    operations = [
        migrations.AlterField(
            model_name='urlsignature',
            name='byline_selector',
            field=models.CharField(default=b'<default>((text))[itemprop~=author];\n((text)).hnews .author .fn;\n((text))[rel=author];((text)).byline', max_length=1000, null=True),
        ),
    ]
