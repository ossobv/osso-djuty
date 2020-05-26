from django.apps import AppConfig
from django.conf import settings
from django.utils import translation

import pyl10n as locale


class L10nAppConfig(AppConfig):
    name = 'osso.l10n'
    verbose_name = 'L10N'

    def ready(self):
        # Set locale path to first path found in LOCALE_PATHS, to override
        # builtin pyl10n locales.
        if len(settings.LOCALE_PATHS) != 0:
            locale.setlocalepath(settings.LOCALE_PATHS[0])

        # Set locale func to follow the standard Django translations.
        locale.setlocalefunc(translation.get_language)
