# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('likeable', '0004_auto_20140915_1445'),
    ]

    operations = [
        migrations.CreateModel(
            name='DownloadedArticle',
            fields=[
                ('article', models.OneToOneField(related_name=b'downloaded', primary_key=True, serialize=False, to='likeable.Article')),
                ('in_dev_sample', models.BooleanField(default=False)),
                ('html', models.TextField()),
                ('headline', models.TextField(null=True)),
                ('dateline', models.TextField(null=True)),
                ('byline', models.TextField(null=True)),
                ('body_html', models.TextField(null=True)),
            ],
            options={
            },
            bases=(models.Model,),
        ),
        migrations.RemoveField(
            model_name='article',
            name='body_html',
        ),
        migrations.RemoveField(
            model_name='article',
            name='byline',
        ),
        migrations.RemoveField(
            model_name='article',
            name='dateline',
        ),
        migrations.RemoveField(
            model_name='article',
            name='download_path',
        ),
        migrations.RemoveField(
            model_name='article',
            name='headline',
        ),
        migrations.RemoveField(
            model_name='article',
            name='in_dev_sample',
        ),
    ]
