from django.conf import settings
from . import pyl10n as locale

__all__ = ('locale',)


# Set locale path to first path found in LOCALE_PATHS
if len(settings.LOCALE_PATHS) != 0:
    locale.setlocalepath(settings.LOCALE_PATHS[0])
