import pyl10n as locale

from django.conf import settings
from django.utils import translation


# Export locale to others.
__all__ = ('locale',)

# Set locale path to first path found in LOCALE_PATHS, to override
# builtin pyl10n locales.
if len(settings.LOCALE_PATHS) != 0:
    locale.setlocalepath(settings.LOCALE_PATHS[0])

# Set locale func to follow the standard Django translations.
locale.setlocalefunc(translation.get_language)
