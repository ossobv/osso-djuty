# vim: set ts=8 sw=4 sts=4 et ai:
import re
import warnings

from django.conf import settings
from django.core.exceptions import MiddlewareNotUsed
from django.utils import translation
from django.utils.cache import patch_vary_headers


# This file is not needed.
warnings.warn(
    'osso.l10n.middleware is deprecated. The django locale middleware '
    'works equally well. Make sure you limit LANGUAGES instead of '
    'LANGUAGE_CODES though.',
    DeprecationWarning, stacklevel=4)

# Format of Accept-Language header values. From RFC 2616, section 14.4 and 3.9.
# (stolen from django and modified)
accept_language_re = re.compile(r'''
    (?:\s*)                                     # Skip whitespace
    (([A-Za-z]{1,8})(?:-[A-Za-z]{1,8})*|\*)     # "en", "en-au", "x-y-z", "*"
    (?:\s*;\s*q=(0(?:\.\d{,3})?|1(?:.0{,3})?))? # Optional "q=1.00", "q=0.8"
    (?:\s*,\s*|\s*$)                            # Multiple accepts per header.
''', re.VERBOSE)


class L10nMiddleware(object):
    '''
    This is an updated version of django's very simple middleware
    that parses a request and decides what translation object to
    install in the current thread context. This allows pages to be
    dynamically translated to the language the user desires.

    The difference with django.middleware.locale.LocaleMiddleware
    is that this one checks settings.LANGUAGE_CODES for valid
    languages.
    '''

    def __init__(self):
        if (not hasattr(settings, 'LANGUAGE_CODES') or
                len(settings.LANGUAGE_CODES) == 0):
            translation.activate(settings.LANGUAGE_CODE)
            raise MiddlewareNotUsed(
                'A fixed language code was set. Not using Accept-Language '
                'headers.')

    def process_request(self, request):
        # Get valid language code from session, cookie or accept headers
        language = self.get_valid_language_from_request(request)
        translation.activate(language)
        request.LANGUAGE_CODE = translation.get_language()

    def process_response(self, request, response):
        patch_vary_headers(response, ('Accept-Language',))
        if 'Content-Language' not in response:
            response['Content-Language'] = translation.get_language()
        translation.deactivate()
        return response

    def get_valid_language_from_request(self, request):
        # Check session language
        if hasattr(request, 'session'):
            lang_code = request.session.get('django_language', None)
            if lang_code in settings.LANGUAGE_CODES:
                return lang_code

        # Check cookie language
        lang_code = request.COOKIES.get(settings.LANGUAGE_COOKIE_NAME)
        if lang_code in settings.LANGUAGE_CODES:
            return lang_code

        # Parse Accept-Header
        languages = self.parse_accept_lang_header(
            request.META.get('HTTP_ACCEPT_LANGUAGE', ''))
        for language in languages:
            # en-us
            if language[0] in settings.LANGUAGE_CODES:
                return language[0]
            # en
            if language[1] in settings.LANGUAGE_CODES:
                return language[1]

        # Return default language
        return settings.LANGUAGE_CODES[0]

    def parse_accept_lang_header(self, lang_string):
        '''
        Parses the lang_string, which is the body of an HTTP Accept-Language
        header, and returns a list of (lang, q-value), ordered by 'q' values.

        Any format errors in lang_string results in an empty list being
        returned.

        (stolen from django and modified)
        '''
        pieces = accept_language_re.findall(lang_string)
        for i, piece in enumerate(pieces):
            pieces[i] = (piece[0], piece[1], float(piece[2] or 1))
        pieces.sort(key=lambda x: x[2], reverse=True)
        return pieces
