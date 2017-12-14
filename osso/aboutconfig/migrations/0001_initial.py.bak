# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations
import osso.core.models.fields


class Migration(migrations.Migration):

    dependencies = [
    ]

    operations = [
        migrations.CreateModel(
            name='Item',
            fields=[
                ('created', models.DateTimeField(auto_now_add=True)),
                ('modified', models.DateTimeField(auto_now=True)),
                ('datatype_id', models.IntegerField(default=1, verbose_name='data type')),
                ('key', osso.core.models.fields.SafeCharField(max_length=63, serialize=False, verbose_name='key', primary_key=True)),
                ('value', models.TextField(verbose_name='value', blank=True)),
            ],
            options={
                'ordering': ('key',),
                'verbose_name': 'advanced/hidden configuration item',
                'verbose_name_plural': 'advanced/hidden configuration items',
            },
            bases=(models.Model,),
        ),
    ]
