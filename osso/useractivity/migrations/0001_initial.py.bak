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
            name='UserActivityLog',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('ip_address', models.IPAddressField(help_text='The IP address of the user when logging in.')),
                ('first_activity', models.DateTimeField(help_text='The time the user logged on.')),
                ('explicit_login', models.BooleanField(default=False, help_text='Whether the login was implicit (reuse of a session) or explicit (the login button).')),
                ('last_activity', models.DateTimeField(help_text="The time of the user's last activity (or logout time, in case explicit_logout is set).", db_index=True)),
                ('explicit_logout', models.NullBooleanField(default=None, help_text='Whether the logout was implicit (idle for too long) or explicit (the logout button).', db_index=True)),
                ('user', models.ForeignKey(help_text="The user we're tracking logins and logouts of.", to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'permissions': (('view_useractivitylog', 'Can view useractivitylog'),),
            },
            bases=(models.Model,),
        ),
    ]
