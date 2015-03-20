# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('likeable', '0019_auto_20150305_1322'),
    ]

    operations = [
        migrations.CreateModel(
            name='Site',
            fields=[
                ('id', models.IntegerField(serialize=False, primary_key=True)),
                ('name', models.TextField()),
                ('url', models.URLField(max_length=256)),
                ('rss_url', models.URLField(max_length=256)),
                ('active', models.BooleanField()),
                ('last_fetch', models.DateTimeField()),
                ('health_start', models.DateTimeField()),
                ('is_healthy', models.BooleanField()),
            ],
        ),
        migrations.AddField(
            model_name='article',
            name='sharewars_site',
            field=models.ForeignKey(to='likeable.Site', null=True),
        ),
        migrations.AddField(
            model_name='sharewarsurl',
            name='site',
            field=models.ForeignKey(to='likeable.Site', null=True),
        ),
    ]
