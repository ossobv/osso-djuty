# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations
from django.conf import settings
import osso.core.models.fields


class Migration(migrations.Migration):

    dependencies = [
        ('auth', '0001_initial'),
        ('relation', '0001_initial'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='Channel',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('created', models.DateTimeField(auto_now_add=True)),
                ('modified', models.DateTimeField(auto_now=True)),
                ('name', osso.core.models.fields.SafeCharField(help_text='The name of the channel, e.g. "Operator chat".', max_length=32)),
                ('max_age', models.PositiveIntegerField(default=86400, help_text='The max age of the messages (in seconds) that are kept for this channel. Set to 0 for eternity.')),
                ('max_count', models.PositiveIntegerField(default=2000, help_text='The max amount of messages that are kept for this channel. Set to 0 for unlimited.')),
                ('groups', models.ManyToManyField(help_text='Users must be a member of one of these groups to read/write to this channel.', to='auth.Group')),
                ('relation', models.ForeignKey(help_text='The relation whose authenticated contacts can read/write to this channel.', to='relation.Relation')),
            ],
            options={
                'ordering': ('id',),
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='Message',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('timestamp', models.DateTimeField(help_text='The time the message was written.', auto_now_add=True)),
                ('body', models.TextField(help_text='The message body.')),
                ('channel', models.ForeignKey(related_name='messages', to='userchat.Channel', help_text='The channel that the message belongs to.')),
                ('sender', models.ForeignKey(related_name='userchat_messages', blank=True, to=settings.AUTH_USER_MODEL, help_text='The user that wrote the message or NULL if it was a system message.', null=True)),
            ],
            options={
            },
            bases=(models.Model,),
        ),
        migrations.AlterUniqueTogether(
            name='channel',
            unique_together=set([('relation', 'name')]),
        ),
    ]
