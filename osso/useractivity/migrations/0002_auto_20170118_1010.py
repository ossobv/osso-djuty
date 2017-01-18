# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('useractivity', '0001_initial'),
    ]

    operations = [
        migrations.AlterField(
            model_name='useractivitylog',
            name='ip_address',
            field=models.GenericIPAddressField(help_text='The IP address of the user when logging in.'),
            preserve_default=True,
        ),
    ]
