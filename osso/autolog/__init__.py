from django.conf import settings


if 'osso.aboutconfig' not in settings.INSTALLED_APPS:
    raise ImportError('Expected app osso.aboutconfig to be loaded!')
