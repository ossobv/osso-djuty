# vim: set ts=8 sw=4 sts=4 et ai:
import datetime

from django.test import TestCase, override_settings
from django.utils import translation

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

    def test_strftime(self):
        self.assertEqual(
            strftime(datetime.datetime(2015, 2, 27, 1, 2, 3, 4),
                     '%y%m%d-%H%M%S'),
            '150227-010203')

    @override_settings(USE_L10N=True)
    def test_strftime_auto(self):
        with translation.override('en'):
            self.assertEqual(
                strftime(datetime.datetime(2015, 2, 27)),
                '2015-02-27 00:00:00')
            self.assertEqual(
                strftime(datetime.date(2015, 2, 27)), '2015-02-27')
            self.assertEqual(
                strftime(datetime.time(22, 12, 10)), '22:12:10')

        with translation.override('nl'):
            self.assertEqual(strftime(datetime.datetime(2015, 2, 27)),
                             '27-02-2015 00:00:00')
            self.assertEqual(
                strftime(datetime.date(2015, 2, 27)), '27-02-2015')

        with translation.override('fi'):
            self.assertEqual(
                strftime(datetime.time(22, 12, 10)), '22.12.10')
