# vim: set ts=8 sw=4 sts=4 et ai:
from django.apps import AppConfig
from django.conf import settings


class AboutConfigAppConfig(AppConfig):
    name = 'osso.aboutconfig'
    verbose_name = 'About Config'

    def ready(self):
        if 'osso.core' not in settings.INSTALLED_APPS:
            raise ImportError('osso.aboutconfig requires osso.core')
