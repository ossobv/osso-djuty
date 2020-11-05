from django.test import TestCase

from .models import Item
from .utils import aboutconfig
from .utils import aboutconfig


class AboutConfigTestCase(TestCase):
    def test_aboutconfig(self):
        item = Item.objects.create(
            key='a.b.c.d.e', value=' \n \r somevalue with \n spaces \t ')
        self.assertEqual(repr(item), '<Item: a.b.c.d.e>')
        self.assertEqual(item.value, 'somevalue with \n spaces')
        self.assertEqual(
            aboutconfig('a.b.c.d.e'), 'somevalue with \n spaces')
        self.assertEqual(aboutconfig('abc'), '')
        self.assertEqual(aboutconfig('abc', 'def'), 'def')
        self.assertEqual(aboutconfig('abc', 123.456), '123.456')
        deleted = Item.objects.filter(key__in=('a.b.c.d.e', 'abc')).delete()
        self.assertEqual(deleted, (1, {'aboutconfig.Item': 1}))
