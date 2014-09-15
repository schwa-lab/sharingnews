# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('likeable', '0003_auto_20140911_1223'),
    ]

    operations = [
        migrations.AlterField(
            model_name='article',
            name='fb_created',
            field=models.DateTimeField(null=True, db_index=True),
        ),
        migrations.AlterIndexTogether(
            name='article',
            index_together=set([('url_signature', 'fb_created')]),
        ),
    ]
