# vim: set ts=8 sw=4 sts=4 et ai tw=79:
"""
Taken from django-pstore and adapted.

Copyright (C) 2012,2013  Walter Doekes <wdoekes>, OSSO B.V.

    This application is free software; you can redistribute it and/or modify
    it under the terms of the GNU Lesser General Public License as published
    by the Free Software Foundation; either version 3 of the License, or (at
    your option) any later version.

    This application is distributed in the hope that it will be useful, but
    WITHOUT ANY WARRANTY; without even the implied warranty of
    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
    Lesser General Public License for more details.

    You should have received a copy of the GNU Lesser General Public
    License along with this application; if not, write to the Free Software
    Foundation, Inc., 59 Temple Place, Suite 330, Boston, MA 02111-1307,
    USA.
"""
try:
    py2 = bool(unicode)
    bchr = chr
except NameError:
    py2 = False
    bchr = lambda i: bytes([i])

import sys

from django.db import models
from django.test import TestCase
try:
    from django.utils.unittest import expectedFailure, skip  # django 1.3+
except ImportError:
    try:
        from unittest import expectedFailure, skip  # django 1.1, new py
    except ImportError:
        expectedFailure, skip = None, None

from osso.mysql.models import AsciiField, BlobField, _db_engines


def expect_failure_if_not_mysql(test_fn):
    if any(i.rsplit('.', 1)[-1] != 'mysql' for i in _db_engines()):
        if expectedFailure:
            return expectedFailure(test_fn)
        return (lambda x: sys.stderr.write('(x)'))  # python 2.6-
    return test_fn


def skip_if_not_mysql_or_sqlite(test_fn):
    if any(i.rsplit('.', 1)[-1] not in ('mysql', 'sqlite3')
           for i in _db_engines()):
        return skip('requires either mysql or sqlite')(test_fn)
    return test_fn


class AsciiModel(models.Model):
    """
    Used by the internal test cases.
    """
    name = AsciiField(max_length=63, blank=True, null=False)
    value = models.PositiveIntegerField()

    class Meta:
        app_label = 'mysql'


class AsciiTest(TestCase):

    @skip_if_not_mysql_or_sqlite
    def test_create(self):
        obj = AsciiModel.objects.create(name=u'unicode-\u20ac', value=1)

        # Lookup by id and check name validity (downcast to ascii)
        obj2 = AsciiModel.objects.get(id=obj.id)
        self.assertEqual(obj2.name, 'unicode-?')

    @skip_if_not_mysql_or_sqlite
    def test_lookup(self):
        obj = AsciiModel.objects.create(name=u'unicode-?', value=2)

        # Lookup by name (should be downcast to ascii)
        obj2 = AsciiModel.objects.get(name=u'unicode-\u20ac')
        self.assertEqual(obj2.id, obj.id)

    @skip_if_not_mysql_or_sqlite
    def test_only(self):
        AsciiModel.objects.create(name=u'unicode-?', value=3)
        values = [i.name for i in AsciiModel.objects.only('name')]
        self.assertEqual(values, [u'unicode-?'])

    @skip_if_not_mysql_or_sqlite
    def test_values(self):
        AsciiModel.objects.create(name=u'unicode-?', value=4)
        values = [i['name'] for i in AsciiModel.objects.values('name')]
        self.assertEqual(values, [u'unicode-?'])

    @skip_if_not_mysql_or_sqlite
    def test_values_list(self):
        AsciiModel.objects.create(name=u'unicode-?', value=5)
        values = list(AsciiModel.objects.values_list('name', flat=True))
        self.assertEqual(values, [u'unicode-?'])

    @skip_if_not_mysql_or_sqlite
    def test_case_sensitive_store(self):
        obj = AsciiModel.objects.create(name='case', value=1)
        obj2 = AsciiModel.objects.create(name='CaSe', value=2)
        obj3 = AsciiModel.objects.create(name='CASE', value=3)
        self.assertEqual(AsciiModel.objects.get(id=obj.id).name, 'case')
        self.assertEqual(AsciiModel.objects.get(id=obj2.id).name, 'CaSe')
        self.assertEqual(AsciiModel.objects.get(id=obj3.id).name, 'CASE')

    @skip_if_not_mysql_or_sqlite
    def test_case_sensitive_lookup(self):
        AsciiModel.objects.create(name='case', value=1)
        AsciiModel.objects.create(name='CaSe', value=2)
        AsciiModel.objects.create(name='CASE', value=3)
        self.assertEqual(AsciiModel.objects.get(name='case').value, 1)
        self.assertEqual(AsciiModel.objects.get(name='CaSe').value, 2)
        self.assertEqual(AsciiModel.objects.get(name='CASE').value, 3)

    @skip_if_not_mysql_or_sqlite
    def test_substring_contains(self):
        AsciiModel.objects.create(name='a Mid-String to search for', value=1)
        AsciiModel.objects.create(name='whatever', value=2)
        self.assertEquals(
            AsciiModel.objects.filter(name__contains='Mid-String').count(), 1)

    @skip_if_not_mysql_or_sqlite
    def test_substring_startswith(self):
        AsciiModel.objects.create(name='a Mid-String to search for', value=1)
        AsciiModel.objects.create(name='whatever', value=2)
        self.assertEquals(
            AsciiModel.objects.filter(name__startswith='a Mid').count(), 1)

    @skip_if_not_mysql_or_sqlite
    def test_substring_endswith(self):
        AsciiModel.objects.create(name='a Mid-String to search for', value=1)
        AsciiModel.objects.create(name='whatever', value=2)
        self.assertEquals(
            AsciiModel.objects.filter(name__endswith='search for').count(), 1)

    @skip_if_not_mysql_or_sqlite
    @expect_failure_if_not_mysql
    def test_substring_contains_case(self):
        AsciiModel.objects.create(name='a Mid-String to search for', value=1)
        AsciiModel.objects.create(name='a mid-string to miss', value=2)
        self.assertEquals(
            AsciiModel.objects.filter(name__contains='Mid-String').count(), 1)

    @skip_if_not_mysql_or_sqlite
    @expect_failure_if_not_mysql
    def test_substring_startswith_case(self):
        AsciiModel.objects.create(name='a Mid-String to search for', value=1)
        AsciiModel.objects.create(name='a mid-string to miss', value=2)
        self.assertEquals(
            AsciiModel.objects.filter(name__startswith='a Mid').count(), 1)

    @skip_if_not_mysql_or_sqlite
    @expect_failure_if_not_mysql
    def test_substring_endswith_case(self):
        AsciiModel.objects.create(name='a Mid-String to search for', value=1)
        AsciiModel.objects.create(name='a mid-string to Search For', value=2)
        self.assertEquals(
            AsciiModel.objects.filter(name__endswith='search for').count(), 1)


class BlobModel(models.Model):
    """
    Used by the internal test cases.
    """
    name = AsciiField(max_length=63, blank=True, null=False)
    value = BlobField(blank=True, null=False)

    class Meta:
        app_label = 'mysql'


class BlobTest(TestCase):

    @skip_if_not_mysql_or_sqlite
    def test_binary(self):
        binary = b'\x00\x01\x02...abc...\xfd\xfe\xff'

        obj = BlobModel.objects.create(name='binary', value=binary)
        obj_id = obj.id
        del obj

        # Lookup and compare
        obj2 = BlobModel.objects.get(id=obj_id)
        self.assertEqual(obj2.value, binary)
        self.assertTrue(isinstance(obj2.value, bytes))  # non-unicode

    @skip_if_not_mysql_or_sqlite
    def test_lowascii(self):
        # Test control characters and check that no one does CRLF
        # replacing.
        binary = b''.join([bchr(i) for i in range(0, 32)]) + b'\r\n\r\n'

        obj = BlobModel.objects.create(name='lowascii', value=binary)
        obj_id = obj.id
        del obj

        # Lookup and compare
        obj2 = BlobModel.objects.get(id=obj_id)
        self.assertEqual(obj2.value, binary)
        self.assertTrue(isinstance(obj2.value, bytes))  # non-unicode

    @skip_if_not_mysql_or_sqlite
    def test_long(self):
        data512 = ((b'A' * 127 + b'\n') + (b'B' * 127 + b'\n') +
                   (b'C' * 127 + b'\n') + (b'C' * 127 + b'\n'))
        data = (4096 * (2 * data512)) + b'..tail'  # 4MB and a little
        self.assertEqual(len(data), 4096 * 1024 + 6)

        obj = BlobModel.objects.create(name='long', value=data)
        obj_id = obj.id
        del obj

        # Lookup and compare
        obj2 = BlobModel.objects.get(id=obj_id)
        self.assertEqual(obj2.value, data)
        self.assertTrue(isinstance(obj2.value, bytes))  # non-unicode

    @skip_if_not_mysql_or_sqlite
    def test_only(self):
        binary = b'\x00\x01\x02...abc...\xfd\xfe\xff'
        BlobModel.objects.create(name='binary', value=binary)
        values = [i.value for i in BlobModel.objects.only('value')]
        self.assertEqual(values, [binary])

    @skip_if_not_mysql_or_sqlite
    @expect_failure_if_not_mysql
    def test_values(self):
        binary = b'\x00\x01\x02...abc...\xfd\xfe\xff'
        BlobModel.objects.create(name='binary', value=binary)
        values = [v['value'] for v in BlobModel.objects.values('value')]

        # Added extra asserts because if we check the equality
        # directly, we get other nasty errors.
        self.assertTrue(values, values)

        # As long as this bug is not fixed:
        # https://code.djangoproject.com/ticket/9619
        # the values will hold the data as it is found in the database,
        # which will not be correct for SQLite3.
        self.assertTrue(isinstance(values[0], bytes), values)
        self.assertEqual(values, [binary])

    @skip_if_not_mysql_or_sqlite
    @expect_failure_if_not_mysql
    def test_values_list(self):
        binary = b'\x00\x01\x02...abc...\xfd\xfe\xff'
        BlobModel.objects.create(name='binary', value=binary)
        values = list(BlobModel.objects.values_list('value', flat=True))

        # Added extra asserts because if we check the equality
        # directly, we get other nasty errors.
        self.assertTrue(values, values)

        # As long as this bug is not fixed:
        # https://code.djangoproject.com/ticket/9619
        # the values will hold the data as it is found in the database,
        # which will not be correct for SQLite3.
        self.assertTrue(isinstance(values[0], bytes), values)
        self.assertEqual(values, [binary])

    @skip_if_not_mysql_or_sqlite
    def test_contains(self):
        binary = b'\x00\x01..ab...\xfe\xff'
        BlobModel.objects.create(name='binary', value=binary)
        BlobModel.objects.create(name='binary2', value='whatever')

        # TypeError: Lookup type exact is not supported.
        self.assertRaises(TypeError, BlobModel.objects.get,
                          value=binary)
        # TypeError: Lookup type contains is not supported.
        self.assertRaises(TypeError, BlobModel.objects.get,
                          value__contains='ab')
