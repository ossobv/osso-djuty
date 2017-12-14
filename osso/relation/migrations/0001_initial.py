# -*- coding: utf-8 -*-


from django.db import models, migrations
from django.conf import settings
import osso.core.models.fields
import sys


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='Address',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('created', models.DateTimeField(auto_now_add=True)),
                ('modified', models.DateTimeField(auto_now=True)),
                ('number', models.PositiveIntegerField(help_text='The house number must be an integer, see the next field for extensions.', verbose_name='number')),
                ('complement', osso.core.models.fields.SafeCharField(help_text='Optional house number suffixes.', max_length=32, verbose_name='complement', blank=True)),
                ('street', osso.core.models.fields.SafeCharField(help_text='The street name, without number.', max_length=127, verbose_name='street')),
                ('zipcode', osso.core.models.fields.SafeCharField(help_text='Zip/postal code.', max_length=16, verbose_name='zip code')),
            ],
            options={
                'ordering': ('relation__name',),
                'verbose_name': 'address',
                'verbose_name_plural': 'addresses',
                'permissions': (('view_address', 'Can view address'),),
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='AddressType',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('created', models.DateTimeField(auto_now_add=True)),
                ('modified', models.DateTimeField(auto_now=True)),
                ('identifier', osso.core.models.fields.SafeCharField(help_text='An identifier for machine lookups: e.g. "BILLING".', max_length=16, verbose_name='identifier')),
                ('description', osso.core.models.fields.SafeCharField(help_text='A descriptive name: e.g. "Postal address".', max_length=63, verbose_name='description')),
            ],
            options={
                'verbose_name': 'address type',
                'verbose_name_plural': 'address types',
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='City',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('created', models.DateTimeField(auto_now_add=True)),
                ('modified', models.DateTimeField(auto_now=True)),
                ('name', osso.core.models.fields.SafeCharField(help_text='The city name.', max_length=63, verbose_name='name')),
            ],
            options={
                'ordering': ('name',),
                'verbose_name': 'city',
                'verbose_name_plural': 'cities',
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='Contact',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('created', models.DateTimeField(auto_now_add=True)),
                ('modified', models.DateTimeField(auto_now=True)),
                ('name', osso.core.models.fields.SafeCharField(help_text='The full name of the contact.', max_length=63, verbose_name='name')),
                ('email', models.EmailField(max_length=75, verbose_name='e-mail address', blank=True)),
            ],
            options={
                'verbose_name': 'contact',
                'verbose_name_plural': 'contacts',
                'permissions': (('view_contact', 'Can view contact'),),
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='AuthenticatableContact',
            fields=[
                ('contact_ptr', models.OneToOneField(parent_link=True, auto_created=True, primary_key=True, serialize=False, to='relation.Contact')),
                ('user', models.OneToOneField(related_name='authenticatablecontact', verbose_name='user', to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'verbose_name': 'authenticatable contact',
                'verbose_name_plural': 'authenticatable contacts',
            },
            bases=('relation.contact',),
        ),
        migrations.CreateModel(
            name='Country',
            fields=[
                ('created', models.DateTimeField(auto_now_add=True)),
                ('modified', models.DateTimeField(auto_now=True)),
                ('code', osso.core.models.fields.SafeCharField(help_text='The ISO 3166 alpha2 code in lowercase.', max_length=2, serialize=False, verbose_name='code', primary_key=True)),
                ('name', osso.core.models.fields.SafeCharField(help_text='The country name.', max_length=63, verbose_name='name')),
                ('order', models.PositiveIntegerField(default=0, help_text='A non-zero number orders the countries highest first in select boxes (use this for commonly used countries).', verbose_name='order')),
            ],
            options={
                'ordering': ('-order', 'name'),
                'verbose_name': 'country',
                'verbose_name_plural': 'countries',
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='PhoneNumber',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('created', models.DateTimeField(auto_now_add=True)),
                ('modified', models.DateTimeField(auto_now=True)),
                ('number', osso.core.models.fields.PhoneNumberField(help_text='The telephone number.', verbose_name='number')),
                ('active', models.BooleanField(default=True, help_text='Whether one should use this number.', verbose_name='active')),
                ('comment', osso.core.models.fields.SafeCharField(help_text='Optional comments about the number\'s use (or "Fax").', max_length=63, verbose_name='comment', blank=True)),
            ],
            options={
                'ordering': ('relation__name',),
                'verbose_name': 'phone number',
                'verbose_name_plural': 'phone numbers',
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='Relation',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('created', models.DateTimeField(auto_now_add=True)),
                ('modified', models.DateTimeField(auto_now=True)),
                ('name', osso.core.models.fields.SafeCharField(help_text='The relation name: a company name or a person name in case of a private person.', max_length=63, verbose_name='name')),
                ('code', osso.core.models.fields.SafeCharField(help_text='A human readable short relation identifier; should be unique per owner.', max_length=16, verbose_name='code', blank=True)),
                ('foreign_code', osso.core.models.fields.SafeCharField(help_text='A human readable identifier that the relation uses to identify you by.', max_length=16, verbose_name='foreign code', blank=True)),
                ('owner', osso.core.models.fields.ParentField(related_name='owned_set', blank=True, to='relation.Relation', help_text='This allows for reseller-style relationships. Set to NULL for the system owner.', null=True, verbose_name='owner')),
            ],
            options={
                'ordering': ('name',),
                'verbose_name': 'relation',
                'verbose_name_plural': 'relations',
                'permissions': (('view_relation', 'Can view relation'),),
            },
            bases=(models.Model,),
        ),
        migrations.AddField(
            model_name='phonenumber',
            name='relation',
            field=models.ForeignKey(related_name='phonenumber_set', verbose_name='relation', to='relation.Relation', help_text='The relation this phone number belongs to.'),
            preserve_default=True,
        ),
        migrations.AddField(
            model_name='contact',
            name='relation',
            field=models.ForeignKey(verbose_name='relation', to='relation.Relation'),
            preserve_default=True,
        ),
        migrations.AddField(
            model_name='city',
            name='country',
            field=models.ForeignKey(verbose_name='country', to='relation.Country', help_text='Select the country the city lies in.'),
            preserve_default=True,
        ),
        migrations.AddField(
            model_name='address',
            name='address_type',
            field=models.ManyToManyField(help_text='Select one or more types of addresses.', to='relation.AddressType', verbose_name='address type'),
            preserve_default=True,
        ),
        migrations.AddField(
            model_name='address',
            name='city',
            field=models.ForeignKey(verbose_name='city', to='relation.City', help_text='The city.'),
            preserve_default=True,
        ),
        migrations.AddField(
            model_name='address',
            name='contact',
            field=models.ForeignKey(blank=True, to='relation.Contact', help_text='For the attention of', null=True),
            preserve_default=True,
        ),
        migrations.AddField(
            model_name='address',
            name='relation',
            field=models.ForeignKey(verbose_name='relation', to='relation.Relation', help_text='The relation this address belongs to.'),
            preserve_default=True,
        ),
    ]
