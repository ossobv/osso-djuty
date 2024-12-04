# vim: set ts=8 sw=4 sts=4 et ai:
# Django settings for testapp project.
import django
from .settings import *  # noqa

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': 'djuty',
        'USER': 'postgres',
        'PASSWORD': '',
        'HOST': '',
        'PORT': '',
    }
}

# Django 2.2 with psycopg2 has issues.
# AssertionError: database connection isn't set to UTC
# SystemError: type psycopg2.extensions.ReplicationConnection has the Py_TPFLAGS_HAVE_GC flag but has no traverse function
if django.VERSION < (3, 0):
    USE_TZ = False
