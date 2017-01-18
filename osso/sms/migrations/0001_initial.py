# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations
import osso.core.models.fields


class Migration(migrations.Migration):

    dependencies = [
        ('relation', '0001_initial'),
    ]

    operations = [
        migrations.CreateModel(
            name='Operator',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('created', models.DateTimeField(auto_now_add=True)),
                ('modified', models.DateTimeField(auto_now=True)),
                ('code', models.PositiveIntegerField(help_text='The GSM operator code, e.g. 8 for 204-08 KPN Telecom.')),
                ('name', osso.core.models.fields.SafeCharField(help_text='A friendly name, e.g. "KPN Telecom".', max_length=64, blank=True)),
            ],
            options={
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='OperatorCountryCode',
            fields=[
                ('country', models.OneToOneField(primary_key=True, serialize=False, to='relation.Country', help_text='The country.')),
                ('code', models.PositiveIntegerField(help_text='A three digit GSM country code.', db_index=True)),
            ],
            options={
                'ordering': ('country__name',),
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='Payout',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('created', models.DateTimeField(auto_now_add=True)),
                ('modified', models.DateTimeField(auto_now=True)),
                ('local_address', osso.core.models.fields.SafeCharField(help_text='Local phone number, e.g. a shortcode. Leave empty to match all.', max_length=32, blank=True)),
                ('tariff_cent', models.PositiveIntegerField(help_text='The MT SMS tariff in cents. Leave NULL to set the MO payout. (Watch out for dupes. The unique constraint will not work with NULL values.)', null=True, blank=True)),
                ('payout_cent', osso.core.models.fields.DecimalField(help_text='The Payout (in cents!) by the GSM operator for this tariff.', max_digits=15, decimal_places=5)),
                ('operator', models.ForeignKey(help_text='The GSM operator.', to='sms.Operator')),
            ],
            options={
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='TextMessage',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('created', models.DateTimeField(help_text='When the text message was created in this system.', auto_now_add=True, db_index=True)),
                ('modified', models.DateTimeField(help_text='When the text message was last modified.', auto_now=True)),
                ('status', models.CharField(help_text='The status of the message (includes direction).', max_length=3, choices=[(b'in', 'Inbound'), (b'rd', 'Inbound read'), (b'out', 'Outbound'), (b'pnd', 'Outbound pending'), (b'nak', 'Outbound failed'), (b'ack', 'Outbound sent')])),
                ('local_address', osso.core.models.fields.SafeCharField(help_text='Local phone number. This does not necessarily need to be a phone number.', max_length=32, blank=True)),
                ('remote_address', osso.core.models.fields.PhoneNumberField(help_text='The phone number of the remote end: the originator on inbound and the recipient on outbound (with country code, without leading zeroes).')),
                ('body', models.TextField(help_text='The message body. In case of a simple messaging server, this should be at most 160 characters long.')),
                ('body_count', models.PositiveIntegerField(default=1, help_text='How many messages this message is composed of.')),
                ('delivery_date', models.DateTimeField(help_text='The delivery date. On an outbound message, this should be set first on acknowledgement of receipt.', null=True, db_index=True, blank=True)),
                ('metadata', models.TextField(help_text='Optional metadata as a pickled python object. By convention this is either None or a list of dictionaries.', blank=True)),
                ('remote_operator', models.ForeignKey(blank=True, to='sms.Operator', help_text='Optionally the GSM operator of the remote end.', null=True)),
            ],
            options={
                'ordering': ('-id', 'remote_address'),
                'permissions': (('view_textmessagestatus', 'Can view textmessage status'),),
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='TextMessageExtra',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('shortcode', models.PositiveIntegerField(help_text='Shortcode that this message was received on, or is sent from.', null=True, blank=True)),
                ('keyword', osso.core.models.fields.SafeCharField(help_text='Keyword that this message was received for, or is sent from.', max_length=63, null=True, blank=True)),
                ('tariff_cent', models.PositiveIntegerField(default=0, help_text='Consumer price (MT) for sent SMS.')),
                ('foreign_reference', osso.core.models.fields.SafeCharField(help_text='Foreign reference (e.g. mid for Mollie).', max_length=31, db_index=True, blank=True)),
                ('foreign_status', osso.core.models.fields.SafeCharField(default=b'', help_text='Same as status, but SMS-provider specific.', max_length=31, blank=True)),
                ('textmessage', models.OneToOneField(related_name='extra', to='sms.TextMessage', help_text='The textmessage that the extra info is about.')),
            ],
            options={
            },
            bases=(models.Model,),
        ),
        migrations.AlterUniqueTogether(
            name='payout',
            unique_together=set([('operator', 'local_address', 'tariff_cent')]),
        ),
        migrations.AddField(
            model_name='operator',
            name='country',
            field=models.ForeignKey(help_text='The country (found through the first part of the code).', to='relation.Country'),
            preserve_default=True,
        ),
        migrations.AlterUniqueTogether(
            name='operator',
            unique_together=set([('code', 'country')]),
        ),
    ]
