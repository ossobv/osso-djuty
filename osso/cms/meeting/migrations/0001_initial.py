# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations
from django.conf import settings


class Migration(migrations.Migration):

    dependencies = [
        ('members', '0001_initial'),
        ('sites', '0001_initial'),
        ('sms', '0001_initial'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='EmailMessage',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('created', models.DateTimeField(auto_now_add=True)),
                ('delivered', models.DateTimeField(null=True, blank=True)),
                ('email_address', models.EmailField(max_length=75)),
                ('subject', models.CharField(max_length=128)),
                ('plain', models.TextField()),
                ('html', models.TextField()),
            ],
            options={
                'abstract': False,
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='EmailStyling',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('style', models.TextField()),
                ('site', models.OneToOneField(related_name='email_styling', to='sites.Site')),
            ],
            options={
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='Invite',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('created', models.DateTimeField(auto_now_add=True)),
                ('accept', models.NullBooleanField()),
                ('token', models.CharField(max_length=16)),
            ],
            options={
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='InviteTextMessage',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('invite', models.ForeignKey(to='meeting.Invite')),
                ('message', models.OneToOneField(to='sms.TextMessage')),
            ],
            options={
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='Meeting',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('email_address', models.EmailField(help_text='Enter your e-mail address.', max_length=75, null=True, verbose_name='E-mail address')),
                ('name', models.CharField(help_text='Enter your name.', max_length=20, verbose_name='Name')),
                ('subject', models.CharField(help_text='Subject of meeting', max_length=25, null=True, verbose_name='Subject', blank=True)),
                ('date', models.DateField(help_text='Date of meeting', verbose_name='Date')),
                ('time', models.TimeField(help_text='Time of meeting', verbose_name='Time')),
                ('pin_code', models.CharField(help_text='Access code of meeting.', max_length=5, verbose_name='Access code')),
                ('group', models.ForeignKey(blank=True, to='members.Group', help_text='Select a group or enter a name to create a new group.', null=True, verbose_name='Group')),
                ('user', models.ForeignKey(blank=True, to=settings.AUTH_USER_MODEL, null=True)),
            ],
            options={
                'ordering': ('-date', '-time'),
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='MeetingTextMessage',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('meeting', models.OneToOneField(to='meeting.Meeting')),
                ('message', models.OneToOneField(to='sms.TextMessage')),
            ],
            options={
            },
            bases=(models.Model,),
        ),
        migrations.AddField(
            model_name='invite',
            name='meeting',
            field=models.ForeignKey(related_name='invites', to='meeting.Meeting'),
            preserve_default=True,
        ),
        migrations.AddField(
            model_name='invite',
            name='member',
            field=models.ForeignKey(related_name='members', to='members.Member'),
            preserve_default=True,
        ),
    ]
