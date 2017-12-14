# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations
import osso.core.models.fields


class Migration(migrations.Migration):

    dependencies = [
    ]

    operations = [
        migrations.CreateModel(
            name='DeliveryReportForward',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('batch_prefix', osso.core.models.fields.SafeCharField(help_text='The batch prefix to match delivery reports.', unique=True, max_length=64)),
                ('destination', models.URLField(help_text='The URL to forward the delivery report to.')),
            ],
            options={
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='DeliveryReportForwardLog',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('datetime', models.DateTimeField(help_text='The datetime the response was forwarded.', auto_now_add=True)),
                ('post_data', osso.core.models.fields.SafeCharField(help_text='The POST data.', max_length=512)),
                ('destination', osso.core.models.fields.SafeCharField(help_text='The destination the delivery report was forwarded to.', max_length=200)),
                ('batch_prefix', osso.core.models.fields.SafeCharField(help_text='The batch prefix that was matched.', max_length=64)),
                ('response', osso.core.models.fields.SafeCharField(help_text='The response from the DLR destination.', max_length=512, blank=True)),
            ],
            options={
            },
            bases=(models.Model,),
        ),
    ]
