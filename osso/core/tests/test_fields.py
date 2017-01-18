# vim: set ts=8 sw=4 sts=4 et ai:
from unittest import skipIf
from django import VERSION
from django.test import TestCase

from osso.core.models.fields import FormatterCharField, FormatterTextField


class FieldTestCase(TestCase):
    @skipIf(VERSION[:2] < (1, 7), 'this test requires django 1.7')
    def test_deconstrcutor(self):
        field = FormatterCharField(max_length=64, format_fields=('date', 'username'),
            clean_value=FormatterCharField.CLEAN_VALUE_DEFAULT)
        name, path, args, kwargs = field.deconstruct()
        clone = FormatterCharField(*args, **kwargs)
        self.assertEqual(field.format_fields, clone.format_fields)
        self.assertEqual(field.accept_newlines, clone.accept_newlines)
        self.assertEqual(field.clean_value, clone.clean_value)

        field = FormatterCharField(max_length=64, format_fields=('date', 'username'),
            clean_value=FormatterCharField.CLEAN_VALUE_WITH_ATTRIBUTES)
        name, path, args, kwargs = field.deconstruct()
        clone = FormatterCharField(*args, **kwargs)
        self.assertEqual(field.format_fields, clone.format_fields)
        self.assertEqual(field.accept_newlines, clone.accept_newlines)
        self.assertEqual(field.clean_value, clone.clean_value)

        field = FormatterTextField(format_fields=('date', 'username'),
            clean_value=FormatterTextField.CLEAN_VALUE_WITH_ATTRIBUTES)
        name, path, args, kwargs = field.deconstruct()
        clone = FormatterTextField(*args, **kwargs)
        self.assertEqual(field.format_fields, clone.format_fields)
        self.assertEqual(field.accept_newlines, clone.accept_newlines)
        self.assertEqual(field.clean_value, clone.clean_value)
