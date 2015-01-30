# vim: set ts=8 sw=4 sts=4 et ai:
from tempfile import NamedTemporaryFile

from django import forms
from django.utils.translation import ugettext_lazy as _

from osso.videmus.utils import get_video_metadata

class VideoField(forms.FileField):
    '''
    A form field that can validate video files.
    '''
    default_error_messages = {
        'invalid_video': _('Upload a valid video. The file you uploaded was either not recognized as a video or a corrupted video.'),
    }

    def to_python(self, data):
        f = super(VideoField, self).to_python(data)
        if f is None:
            return None

        try:
            # we need a physical file for validation
            if hasattr(data, 'temporary_file_path'):
                get_video_metadata(data.temporary_file_path(), validate=True)
            else:
                # file is stored in memory
                with NamedTemporaryFile() as tmpfile:
                    if hasattr(data, 'read'):
                        tmpfile.write(data.read())
                    else:
                        tmpfile.write(data['content'])
                    tmpfile.flush()
                    get_video_metadata(tmpfile.name, validate=True)
        except ValueError:
            raise forms.ValidationError(self.error_messages['invalid_video'])
        if hasattr(f, 'seek') and callable(f.seek):
            f.seek(0)
        return f
