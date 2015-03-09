# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('likeable', '0020_auto_20150305_1323'),
    ]

    operations = [
        migrations.CreateModel(
            name='AggregateStatistic',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('name', models.CharField(max_length=100)),
                ('base_domain', models.CharField(max_length=50, null=True)),
                ('start', models.DateField(max_length=50)),
                ('stop', models.DateField(max_length=50)),
                ('fb_count_5d_centre', models.PositiveIntegerField(null=True)),
                ('fb_count_longterm_centre', models.PositiveIntegerField(null=True)),
                ('tw_count_5d_centre', models.PositiveIntegerField(null=True)),
                ('tw_count_longterm_centre', models.PositiveIntegerField(null=True)),
                ('fb_count_5d_scale', models.PositiveIntegerField(null=True)),
                ('fb_count_longterm_scale', models.PositiveIntegerField(null=True)),
                ('tw_count_5d_scale', models.PositiveIntegerField(null=True)),
                ('tw_count_longterm_scale', models.PositiveIntegerField(null=True)),
            ],
        ),
        migrations.AlterField(
            model_name='site',
            name='health_start',
            field=models.DateTimeField(null=True),
        ),
        migrations.AlterField(
            model_name='site',
            name='is_healthy',
            field=models.NullBooleanField(),
        ),
        migrations.AlterField(
            model_name='site',
            name='last_fetch',
            field=models.DateTimeField(null=True),
        ),
        migrations.AlterField(
            model_name='site',
            name='rss_url',
            field=models.URLField(max_length=256, null=True),
        ),
        migrations.AlterIndexTogether(
            name='aggregatestatistic',
            index_together=set([('name', 'base_domain', 'start')]),
        ),
    ]
