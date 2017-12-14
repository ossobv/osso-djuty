# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations
from django.conf import settings


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='Payment',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('created', models.DateTimeField(help_text='When this object was created.', verbose_name='created', auto_now_add=True)),
                ('realm', models.CharField(help_text='Realm/domain/host where this payment is done (e.g. yoursite1.com); include scheme:// so we know where to return your request.', max_length=127, verbose_name='realm', blank=True)),
                ('description', models.CharField(help_text='A description of the payment. Keep it short.', max_length=255, verbose_name='description')),
                ('amount', models.DecimalField(help_text='The amount of money being transferred.', verbose_name='amount', max_digits=9, decimal_places=2)),
                ('currency', models.CharField(help_text='The currency of the transaction (e.g. EUR/USD) or empty if currency-agnostic.', max_length=3, verbose_name='currency', blank=True)),
                ('transfer_initiated', models.DateTimeField(help_text='When the request to the bank was made.', null=True, verbose_name='transfer initiated', blank=True)),
                ('transfer_allowed', models.DateTimeField(help_text='When the bank responsed positively.', null=True, verbose_name='transfer allowed', blank=True)),
                ('transfer_finalized', models.DateTimeField(help_text='When the bank confirmed/reject the transaction.', null=True, verbose_name='transfer finalized', blank=True)),
                ('transfer_revoked', models.DateTimeField(help_text='If the bank revoked the transaction after finalizing it.', null=True, verbose_name='transfer revoked', blank=True)),
                ('is_success', models.NullBooleanField(editable=False, help_text='Is None until transfer_finalized is set at which point it is True for success and False for failure. If for some reason the transaction is revoked after success, it can flip from True to False.', verbose_name='is success', db_index=True)),
                ('unique_key', models.CharField(help_text='Max. 64 bytes of unique key, e.g. randbits||-||pk. Will be unique if set.', max_length=64, verbose_name='unique key', db_index=True, blank=True)),
                ('blob', models.TextField(help_text='Can hold free form data about the transaction. Use it to store transaction and/or debug info from the bank.', verbose_name='blob', blank=True)),
                ('paying_user', models.ForeignKey(blank=True, to=settings.AUTH_USER_MODEL, help_text='The user which is making the payment, if applicable.', null=True, verbose_name='paying user')),
            ],
            options={
                'verbose_name': 'payment',
                'verbose_name_plural': 'payments',
            },
            bases=(models.Model,),
        ),
    ]
