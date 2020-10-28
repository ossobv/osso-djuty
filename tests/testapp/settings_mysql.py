# vim: set ts=8 sw=4 sts=4 et ai:
# Django settings for testapp project.
from .settings import *  # noqa

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.mysql',
        'NAME': 'djuty',
        'USER': 'djuty',
        'PASSWORD': '',
        'HOST': '127.0.0.1',
        'PORT': '',
    }
}
