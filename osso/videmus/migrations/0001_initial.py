# -*- coding: utf-8 -*-


from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
    ]

    operations = [
        migrations.CreateModel(
            name='VideoSetting',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('format', models.CharField(help_text='The format the video will be encoded to.', max_length=8, verbose_name='format', choices=[(b'flv', 'Flash'), (b'mp4', 'H264'), (b'ogv', 'Ogg Theora'), (b'webm', 'VP8/WebM')])),
                ('size', models.CharField(help_text='The size the video will be encoded to.', max_length=16, verbose_name='format', choices=[(b'426x240', '240p (426x240)'), (b'640x360', '360p (640x360)'), (b'854x480', '480p (854x480)'), (b'1280x720', '720p (1280x720)'), (b'1920x1080', '1080p (1920x1080)')])),
            ],
            options={
            },
            bases=(models.Model,),
        ),
        migrations.AlterUniqueTogether(
            name='videosetting',
            unique_together=set([('format', 'size')]),
        ),
    ]
