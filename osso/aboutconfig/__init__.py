# vim: set ts=8 sw=4 sts=4 et ai:
from django.conf import settings


if 'osso.core' not in settings.INSTALLED_APPS:
    raise ImportError('osso.aboutconfig requires osso.core')
