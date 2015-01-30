from django.conf import settings
from osso.l10n.tests.test_middleware import *


# Make sure the middleware is loaded if we're going to test it.
if 'osso.l10n.middleware.L10nMiddleware' not in settings.MIDDLEWARE_CLASSES:
    settings.MIDDLEWARE_CLASSES += ('osso.l10n.middleware.L10nMiddleware',)
