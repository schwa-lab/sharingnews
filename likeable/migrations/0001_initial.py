# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
    ]

    operations = [
        migrations.CreateModel(
            name='Article',
            fields=[
                ('id', models.BigIntegerField(help_text=b"Facebook's numeric ID", serialize=False, primary_key=True)),
                ('url', models.URLField(max_length=1000)),
                ('fb_updated', models.DateTimeField(null=True)),
                ('fb_type', models.CharField(max_length=35, null=True)),
                ('fb_has_title', models.BooleanField(default=False, db_index=True)),
                ('title', models.CharField(max_length=1000, null=True)),
                ('description', models.TextField(null=True)),
                ('total_shares', models.PositiveIntegerField(null=True)),
                ('fb_created', models.DateTimeField(null=True)),
            ],
            options={
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='ShareWarsUrl',
            fields=[
                ('id', models.BigIntegerField(serialize=False, primary_key=True)),
                ('when', models.DateTimeField(help_text=b'spider time', null=True)),
            ],
            options={
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='SpideredUrl',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('url', models.URLField(unique=True, max_length=1000, db_index=True)),
                ('article', models.ForeignKey(to='likeable.Article', null=True)),
            ],
            options={
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='UrlSignature',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('signature', models.CharField(unique=True, max_length=256, db_index=True)),
                ('base_domain', models.CharField(max_length=50, db_index=True)),
            ],
            options={
            },
            bases=(models.Model,),
        ),
        migrations.AddField(
            model_name='spideredurl',
            name='url_signature',
            field=models.ForeignKey(to='likeable.UrlSignature', null=True),
            preserve_default=True,
        ),
        migrations.AddField(
            model_name='sharewarsurl',
            name='spidered',
            field=models.ForeignKey(to='likeable.SpideredUrl', null=True),
            preserve_default=True,
        ),
        migrations.AddField(
            model_name='article',
            name='url_signature',
            field=models.ForeignKey(to='likeable.UrlSignature', null=True),
            preserve_default=True,
        ),
    ]
