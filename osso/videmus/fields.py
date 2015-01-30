# vim: set ts=8 sw=4 sts=4 et ai:
from django.db.models import FileField, signals
from django.db.models.fields.files import FileDescriptor, FieldFile
from django.utils.translation import ugettext_lazy as _

from osso.videmus.utils import get_video_metadata
from osso.videmus import form_fields


class VideoDescriptor(FileDescriptor):
    '''
    Descriptor that sets metadata fields if they are configured.
    '''
    def __set__(self, instance, value):
        previous_file = instance.__dict__.get(self.field.name)
        super(VideoDescriptor, self).__set__(instance, value)
        if previous_file is not None:
            self.field.update_metadata_fields(instance, force=True)


class FieldVideoFile(FieldFile):
    '''
    FieldFile with additional attributes to access Video metadata.
    '''
    @property
    def width(self):
        return self._get_metadata()[0]

    @property
    def height(self):
        return self._get_metadata()[1]

    @property
    def bitrate(self):
        return self._get_metadata()[2]

    @property
    def fps(self):
        return self._get_metadata()[3]

    @property
    def length(self):
        return self._get_metadata()[4]

    def _get_metadata(self):
        if not hasattr(self, '_metadata_cache'):
            self._metadata_cache = get_video_metadata(self)
        return self._metadata_cache


class VideoField(FileField):
    '''
    A FileField with a few extensions to access video metadata.
    Optionally stores the metadata in fields on the model when saved/changed.
    '''
    attr_class = FieldVideoFile
    descriptor_class = VideoDescriptor
    description = _('Video path')

    def __init__(self, verbose_name=None, name=None, width_field=None,
            height_field=None, bitrate_field=None, fps_field=None,
            length_field=None, **kwargs):
        self.width_field, self.height_field = width_field, height_field
        self.bitrate_field, self.fps_field = bitrate_field, fps_field
        self.length_field = length_field
        super(VideoField, self).__init__(verbose_name, name, **kwargs)

    def contribute_to_class(self, cls, name):
        super(VideoField, self).contribute_to_class(cls, name)
        signals.post_init.connect(self.update_metadata_fields, sender=cls)

    def update_metadata_fields(self, instance, force=False, *args, **kwargs):
        has_metadata_fields = self.width_field or self.height_field \
                or self.bitrate_field or self.fps_field or self.length_field
        if not has_metadata_fields:
            return

        file = getattr(instance, self.attname)

        if not file and not force:
            return

        metadata_fields_filled = not (
            (self.width_field and not getattr(instance, self.width_field))
            or (self.height_field and not getattr(instance, self.height_field))
            or (self.bitrate_field and not getattr(instance, self.bitrate_field))
            or (self.fps_field and not getattr(instance, self.fps_field))
            or (self.length_field and not getattr(instance, self.length_field))
        )
        if metadata_fields_filled and not force:
            return

        if file:
            width = file.width
            height = file.height
            bitrate = file.bitrate
            fps = file.fps
            length = file.length
        else:
            width = height = bitrate = fps = length = None

        if self.width_field:
            setattr(instance, self.width_field, width)
        if self.height_field:
            setattr(instance, self.height_field, height)
        if self.bitrate_field:
            setattr(instance, self.bitrate_field, bitrate)
        if self.fps_field:
            setattr(instance, self.fps_field, fps)
        if self.length_field:
            setattr(instance, self.length_field, length)

    def formfield(self, **kwargs):
        defaults = {'form_class': form_fields.VideoField}
        defaults.update(kwargs)
        return super(VideoField, self).formfield(**defaults)
