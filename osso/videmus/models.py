# vim: set ts=8 sw=4 sts=4 et ai:
import os.path
import sys
import uuid

from django.conf import settings
from django.core.files.storage import FileSystemStorage
from django.core.signals import request_finished
from django.db import models
from django.db.models.base import ModelBase
try:
    from django.utils.encoding import smart_text
except ImportError:
    from django.utils.encoding import smart_unicode as smart_text
from django.utils.translation import ugettext_lazy as _

from osso.videmus.fields import VideoField


VIDEO_ROOT = getattr(settings, 'VIDEO_ROOT', settings.MEDIA_ROOT)
VIDEO_URL = getattr(settings, 'VIDEO_URL', settings.MEDIA_URL)
VIDEO_DIR = getattr(settings, 'VIDEO_DIR', 'video')

storage = FileSystemStorage(location=VIDEO_ROOT, base_url=VIDEO_URL)

VIDEO_FORMAT_CHOICES = (
    ('flv', _('Flash')),
    ('mp4', _('H264')),
    ('ogv', _('Ogg Theora')),
    ('webm', _('VP8/WebM')),
)

VIDEO_SIZE_CHOICES = (
    ('426x240', _('240p (426x240)')),
    ('640x360', _('360p (640x360)')),
    ('854x480', _('480p (854x480)')),
    ('1280x720', _('720p (1280x720)')),
    ('1920x1080', _('1080p (1920x1080)')),
)


class VideoSetting(models.Model):
    '''
    Model to store video encoding settings.
    '''
    format = models.CharField(_('format'), max_length=8,
        choices=VIDEO_FORMAT_CHOICES,
        help_text=_('The format the video will be encoded to.'))
    size = models.CharField(_('format'), max_length=16,
        choices=VIDEO_SIZE_CHOICES,
        help_text=_('The size the video will be encoded to.'))

    @property
    def width(self):
        return int(self.size.split('x')[0])

    @property
    def height(self):
        return int(self.size.split('x')[1])

    def __unicode__(self):
        return '%s %s' % (self.get_format_display(), self.get_size_display())

    class Meta:
        unique_together = (
            ('format', 'size'),
        )


class VideoFileBase(models.Model):
    '''
    Abstract model that can store a video file
    and set additional metadata fields on the model.
    '''
    video = VideoField(_('video'),
        upload_to=(lambda i, fn: i.get_storage_path(fn)),
        storage=storage, width_field='width', height_field='height',
        bitrate_field='bitrate', fps_field='fps', length_field='length')
    is_encoded = models.BooleanField(default=False, editable=False)
    width = models.PositiveIntegerField(null=True, editable=False)
    height = models.PositiveIntegerField(null=True, editable=False)
    bitrate = models.PositiveIntegerField(null=True, editable=False)
    fps = models.PositiveIntegerField(null=True, editable=False)
    length = models.TimeField(null=True, editable=False)

    class Meta:
        abstract = True

    def get_storage_path(self, filename):
        if not hasattr(self, 'format'):
            raise ValueError('VideoFile instance does not specify a format')
        if self.width and self.height:
            filename, extension = os.path.splitext(filename)
            filename = '%s-%dx%d%s' % (filename, self.width, self.height,
                                       extension)
        return os.path.join(VIDEO_DIR, self.format, filename)

    def get_image_storage_path(self, format, filename):
        return os.path.join(VIDEO_DIR, format, filename)

    def __str__(self):
        return str(self).encode('utf-8')

    def __unicode__(self):
        return smart_text(self.video)

    def __repr__(self):
        return '<%s: %s>' % (self.__class__.__name__, self)


class VideoMetaClass(ModelBase):
    '''
    MetaClass for the abstract ``Video`` model.

    Generates a subclass of ``VideoFile`` with a foreignkey relation
    for each subclass of ``Video``.
    '''
    def __new__(cls, name, bases, attrs):
        new_cls = super(VideoMetaClass, cls).__new__(cls, name, bases, attrs)
        parents = [b for b in bases if isinstance(b, VideoMetaClass)]
        if not parents or new_cls._meta.abstract or new_cls._meta.proxy \
                or hasattr(new_cls, 'videofile_set'):
            return new_cls

        # create a subclass of VideoFile for the new Video class
        # with the required relation VideoFile(original=Video())
        child_name = '%sFile' % name
        child_attrs = {
            '__module__': new_cls.__module__,
            'original': models.ForeignKey(new_cls,
                                          related_name='videofile_set'),
        }
        child_bases = (VideoFile,)
        if hasattr(new_cls, 'videofile_mixin'):
            child_bases = (new_cls.videofile_mixin,) + child_bases
        child_class = type(child_name, child_bases, child_attrs)
        # add it to the module namespace
        setattr(sys.modules[new_cls.__module__], child_name, child_class)
        return new_cls


class VideoManager(models.Manager):
    # has_initial_video check does not work if the video
    # is created with create on the Manager
    def create(self, *args, **kwargs):
        video = super(VideoManager, self).create(*args, **kwargs)
        video.encode_video()
        return video

    def get_or_create(self, *args, **kwargs):
        video, created = super(VideoManager, self).create(*args, **kwargs)
        if created:
            video.encode_video()
        return video, created


class Video(VideoFileBase, metaclass=VideoMetaClass):
    '''
    Abstract ``Video`` model that can store and encode a video file.
    '''

    format = 'original'

    objects = VideoManager()

    class Meta:
        abstract = True

    def __init__(self, *args, **kwargs):
        super(Video, self).__init__(*args, **kwargs)
        self.has_initial_video = self.video and True or False

    def encode_video(self, **kwargs):
        from osso.videmus.tasks import encode_video
        encode_video.delay(self.__class__, self.pk)
        if hasattr(self, 'signal_uuid'):
            request_finished.disconnect(
                dispatch_uid='encode_video_%s' % self.signal_uuid, weak=False)

    def save(self, *args, **kwargs):
        super(Video, self).save(*args, **kwargs)
        if not hasattr(self, 'signal_uuid') and not self.has_initial_video:
            self.signal_uuid = uuid.uuid4()
            request_finished.connect(
                self.encode_video, weak=False,
                dispatch_uid='encode_video_%s' % self.signal_uuid)

    @property
    def encoded_files(self):
        return self.videofile_set.filter(is_encoded=True)


class VideoFile(VideoFileBase):
    '''
    Abstract ``VideoFile`` model that stores an encoded ``Video``.
    '''
    # when Video is subclassed a new VideoFile class is created
    # in the same module as the Video subclass using this relation
    # original = models.ForeignKey(Video)
    format = models.CharField(_('format'), max_length=8,
        choices=VIDEO_FORMAT_CHOICES,
        help_text=_('The format the video will be encoded to.'))

    class Meta:
        abstract = True
