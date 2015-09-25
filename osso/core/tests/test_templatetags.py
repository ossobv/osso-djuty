# vim: set ts=8 sw=4 sts=4 et ai:
import datetime

from django.conf import settings
from django.test import TestCase
from django.utils.translation import activate, get_language

from ..templatetags.core import hourstohuman
try:
    from ..templatetags.core import strftime
except ImportError:
    strftime = None


class CoreTemplatetagsTestCase(TestCase):
    def test_hourstohuman(self):
        self.assertEqual(hourstohuman('0.25'), '0:15')
        self.assertEqual(hourstohuman('3.5'), '3:30')
        self.assertEqual(hourstohuman('3.5085'), '3:30:30')

    if strftime:
        def test_strftime(self):
            self.assertEqual(
                strftime(datetime.datetime(2015, 2, 27, 1, 2, 3, 4),
                         '%y%m%d-%H%M%S'),
                '150227-010203')

        def test_strftime_auto(self):
            orig_language = get_language()
            orig_l10n = settings.USE_L10N

            settings.USE_L10N = True
            try:
                activate('en')
                self.assertEqual(strftime(datetime.datetime(2015, 2, 27)),
                                 '2015-02-27 00:00:00')
                self.assertEqual(strftime(datetime.date(2015, 2, 27)),
                                 '2015-02-27')
                self.assertEqual(strftime(datetime.time(22, 12, 10)),
                                 '22:12:10')

                activate('nl')
                self.assertEqual(strftime(datetime.datetime(2015, 2, 27)),
                                 '27-02-2015 00:00:00')
                self.assertEqual(strftime(datetime.date(2015, 2, 27)),
                                 '27-02-2015')

                activate('hu')
                self.assertEqual(strftime(datetime.time(22, 12, 10)),
                                 '22.12.10')
            finally:
                activate(orig_language)
                settings.USE_L10N = orig_l10n
