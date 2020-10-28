# vim: set ts=8 sw=4 sts=4 et ai:
# Django settings for testapp project.
from .settings import *  # noqa

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': 'djuty',
        'USER': 'djuty',
        'PASSWORD': '',
        'HOST': '',
        'PORT': '',
    }
}
