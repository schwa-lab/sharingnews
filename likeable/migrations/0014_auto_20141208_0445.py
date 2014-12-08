# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('likeable', '0013_auto_20141118_1405'),
    ]

    operations = [
        migrations.RenameField(
            model_name='article',
            old_name='total_shares',
            new_name='fb_count_longterm',
        ),
        migrations.AddField(
            model_name='article',
            name='fb_count_2h',
            field=models.PositiveIntegerField(null=True),
            preserve_default=True,
        ),
        migrations.AddField(
            model_name='article',
            name='fb_count_5d',
            field=models.PositiveIntegerField(null=True),
            preserve_default=True,
        ),
        migrations.AddField(
            model_name='article',
            name='fb_count_initial',
            field=models.PositiveIntegerField(null=True),
            preserve_default=True,
        ),
        migrations.AddField(
            model_name='article',
            name='fb_count_1d',
            field=models.PositiveIntegerField(null=True),
            preserve_default=True,
        ),
        migrations.AddField(
            model_name='article',
            name='tw_count_1d',
            field=models.PositiveIntegerField(null=True),
            preserve_default=True,
        ),
        migrations.AddField(
            model_name='article',
            name='tw_count_2h',
            field=models.PositiveIntegerField(null=True),
            preserve_default=True,
        ),
        migrations.AddField(
            model_name='article',
            name='tw_count_5d',
            field=models.PositiveIntegerField(null=True),
            preserve_default=True,
        ),
        migrations.AddField(
            model_name='article',
            name='tw_count_initial',
            field=models.PositiveIntegerField(null=True),
            preserve_default=True,
        ),
        migrations.AddField(
            model_name='article',
            name='tw_count_longterm',
            field=models.PositiveIntegerField(null=True),
            preserve_default=True,
        ),
        migrations.AlterIndexTogether(
            name='article',
            index_together=set([('fetch_status', 'url_signature'), ('fb_count_longterm', 'url_signature'), ('url_signature', 'fb_created')]),
        ),
    ]
