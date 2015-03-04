# vim: set ts=8 sw=4 sts=4 et ai:
import warnings

from django import VERSION as django_version
from django.db import connection, models
from osso.core.forms import fields
from osso.core.types import cidr4


class SafeCharField(models.CharField):
    '''
    A CharField that silently discards all non-printable characters
    below the space (except tab).
    '''
    def formfield(self, **kwargs):
        defaults = {
            'form_class': fields.SafeCharField,
        }
        defaults.update(kwargs)
        return super(SafeCharField, self).formfield(**defaults)


class Cidr4Field(models.Field):
    '''
    An IPv4 address with netmask field.
    '''
    __metaclass__ = models.SubfieldBase

    def __init__(self, **kwargs):
        assert 'max_length' not in kwargs
        kwargs['max_length'] = 18
        super(Cidr4Field, self).__init__(**kwargs)

    def get_internal_type(self):
        return "CharField"

    def to_python(self, value):
        # to_python will be called at ModelForm instantiation with ''
        # as initial value, hence we must accept it as valid value
        if value in (None, ''):
            return None
        return cidr4(value)

    if django_version < (1, 2):
        def get_db_prep_value(self, value):
            return self.get_prep_value(value)

    def get_prep_value(self, value):
        if value is None:
            return None
        value = cidr4(value)
        # Ugly storage method to get proper sorting
        # (A CIDR DB field (postgres has it) or two integer fields
        # would be better.)
        return '%03d.%03d.%03d.%03d/%02d' % (
            (value.address >> 24) & 0xff,
            (value.address >> 16) & 0xff,
            (value.address >> 8) & 0xff,
            (value.address) & 0xff,
            value.sigbits
        )

    def formfield(self, **kwargs):
        defaults = {
            'form_class': fields.Cidr4Field,
        }
        defaults.update(kwargs)
        return super(Cidr4Field, self).formfield(**defaults)


class DecimalField(models.DecimalField):
    '''
    DecimalField with common defaults.
    '''
    def __init__(self, *args, **kwargs):
        if 'decimal_places' not in kwargs:
            kwargs['decimal_places'] = 5
        if 'max_digits' not in kwargs:
            kwargs['max_digits'] = 15
        super(DecimalField, self).__init__(*args, **kwargs)


class EditableSelectField(SafeCharField):
    '''
    A SafeCharField that allows the user to choose from a list of used
    values or enter a new one.
    '''
    def contribute_to_class(self, cls, name):
        self.model = cls
        self.db_column = name
        super(EditableSelectField, self).contribute_to_class(cls, name)

    def formfield(self, **kwargs):
        # I'm not getting this queryset quite right.
        # self.model._default_manager.only(self.column).aggregate... ??
        # So.. we're using custom SQL instead. At least I can type that
        # blindly.
        class queryset(object):
            def __init__(self, table_name, column_name):
                qn = connection.ops.quote_name
                self.column_name = column_name
                self.sql = ('SELECT COUNT(*) AS c, %(c)s FROM %(t)s '
                            'GROUP BY %(c)s ORDER BY c DESC, %(c)s ASC')
                self.sql %= {'t': qn(table_name), 'c': qn(column_name)}

            def all(self):
                class obj(object):
                    def __init__(self, column_name, value):
                        setattr(self, column_name, value)
                cursor = connection.cursor()
                cursor.execute(self.sql)
                return [obj(self.column_name, i[1]) for i in cursor.fetchall()]

        defaults = {
            'to_field_name': self.column,
            'form_class': fields.EditableSelectField,
            'queryset': queryset(self.model._meta.db_table, self.db_column),
        }
        defaults.update(kwargs)
        return super(EditableSelectField, self).formfield(**defaults)


class FormatterBaseField(object):
    '''
    A field that holds stored message templates with the new python 2.6
    str.format() curly brace syntax. E.g. "Today is {date}." where
    'date' is specified as one of the format_fields.

    The convenience is that it does validation on the format fields at
    save time (which is why you need to supply all possibilities in the
    format_fields iterable).
    '''
    CLEAN_VALUE_DEFAULT = \
        fields.FormatterCharField.CLEAN_VALUE_DEFAULT
    CLEAN_VALUE_WITH_ATTRIBUTES = \
        fields.FormatterCharField.CLEAN_VALUE_WITH_ATTRIBUTES

    def __init__(self, format_fields, clean_value=None,
                 accept_newlines=False):
        self.format_fields = tuple(format_fields)
        self.accept_newlines = accept_newlines

        if clean_value is None:
            self.clean_value = self.CLEAN_VALUE_DEFAULT
        else:
            self.clean_value = clean_value

    def formfield(self, **kwargs):
        defaults = {
            'form_class': fields.FormatterCharField,
            'format_fields': self.format_fields,
            'clean_value': self.clean_value,
            'accept_newlines': self.accept_newlines,
        }
        defaults.update(kwargs)
        return super(FormatterBaseField, self).formfield(**defaults)


class FormatterCharField(FormatterBaseField, models.CharField):
    def __init__(self, *args, **kwargs):
        FormatterBaseField.__init__(
            self, format_fields=kwargs.pop('format_fields'),
            clean_value=kwargs.pop('clean_value', None))
        models.CharField.__init__(self, *args, **kwargs)


class FormatterTextField(FormatterBaseField, models.TextField):
    def __init__(self, *args, **kwargs):
        FormatterBaseField.__init__(
            self, format_fields=kwargs.pop('format_fields'),
            clean_value=kwargs.pop('clean_value', None), accept_newlines=True)
        models.TextField.__init__(self, *args, **kwargs)


class NonReversibleForeignKey(models.ForeignKey):
    '''
    The same ForeignKey as always, but this one autogenerates new
    related names. This way you can add many foreign keys to the same
    model from one model.

    See django ticket 5537: http://code.djangoproject.com/ticket/5537
    '''
    __counter = 0

    def __init__(self, *args, **kwargs):
        warnings.warn(
            "'osso.core.models.NonReversibleForeignKey' is deprecated. Since "
            "Django 1.2 you can use related_name='+' instead. See: "
            "https://github.com/django/django/commit/52e7812901",
            DeprecationWarning
        )
        assert 'related_name' not in kwargs, \
            'The point of this model was to skip the related name!'
        super(NonReversibleForeignKey, self).__init__(*args, **kwargs)

    def contribute_to_related_class(self, cls, related):
        NonReversibleForeignKey.__counter += 1
        self.rel.related_name = ('nonreversible_fk_%d' %
                                 NonReversibleForeignKey.__counter)
        return (super(NonReversibleForeignKey, self)
                .contribute_to_related_class(cls, related))


class NonReversibleManyToManyField(models.ManyToManyField):
    '''
    The same ManyToManyField as always, but this one autogenerates new
    related names. This way you can reuse abstract classes with a
    ManyToManyField in the base class.

    See django ticket 5537: http://code.djangoproject.com/ticket/5537

    Note: you can often get away with using "%(class)s" in the
    related_name instead.
    '''
    __counter = 0

    def __init__(self, *args, **kwargs):
        warnings.warn(
            "'osso.core.models.NonReversibleManyToManyField' is deprecated. "
            "Since Django 1.4 you can use related_name='+' instead. See: "
            "https://github.com/django/django/commit/52e7812901",
            PendingDeprecationWarning
        )
        assert 'related_name' not in kwargs, \
            'The point of this model was to skip the related name!'
        super(NonReversibleManyToManyField, self).__init__(*args, **kwargs)

    def contribute_to_related_class(self, cls, related):
        NonReversibleManyToManyField.__counter += 1
        self.rel.related_name = ('nonreversible_m2m_%d' %
                                 NonReversibleManyToManyField.__counter)
        return (super(NonReversibleManyToManyField, self)
                .contribute_to_related_class(cls, related))


class NonReversibleOneToOneField(models.OneToOneField):
    '''
    The same OneToOneField as always, but this one autogenerates new
    related names. This way you can reuse abstract classes with a
    OneToOneField in the base class.

    See django ticket 5537: http://code.djangoproject.com/ticket/5537

    Note: you can often get away with using "%(class)s" in the
    related_name instead.
    '''
    __counter = 0

    def __init__(self, *args, **kwargs):
        warnings.warn(
            "'osso.core.models.NonReversibleOneToOneField' is deprecated. "
            "Since Django 1.2 you can use related_name='+' instead. See: "
            "https://github.com/django/django/commit/52e7812901",
            DeprecationWarning
        )
        assert 'related_name' not in kwargs, \
            'The point of this model was to skip the related name!'
        super(NonReversibleOneToOneField, self).__init__(*args, **kwargs)

    def contribute_to_related_class(self, cls, related):
        NonReversibleOneToOneField.__counter += 1
        self.rel.related_name = ('nonreversible_o2o_%d' %
                                 NonReversibleOneToOneField.__counter)
        return (super(NonReversibleOneToOneField, self)
                .contribute_to_related_class(cls, related))


class ParentField(models.ForeignKey):
    '''
    A foreign key field that points to the model that uses it. Use it to
    define non-cyclic parent-child relationships.
    '''
    def __init__(self, verbose_name=None, **kwargs):
        # Must be null/blank because at least one God object does not
        # have a parent.
        super(ParentField, self).__init__('self', verbose_name=verbose_name,
                                          blank=True, null=True, **kwargs)

    @staticmethod
    def check(object=None, attname=None):
        '''
        Use this static method to check your model instance against
        cyclic relations.
        '''
        # Bah! The check function is used by newer Django (1.7+?).
        if object is None and attname is None:
            return []

        if object.pk is not None:
            parents = set((object.pk,))
            parent = getattr(object, attname)
            while parent is not None:
                assert parent.pk not in parents, \
                    ('%s field disallows cyclic relations (degree %d)' %
                     (attname, len(parents) - 1))
                parents.add(parent.pk)
                parent = (parent.owner, object.owner)[(object.pk == parent.pk)]


class PhoneNumberField(models.Field):
    '''
    A phone number field as a decimal with enough digits to fit any
    real world phone number, including extra long numbers with internal
    routing prefixes.

    The number is stored as a decimal, but in python it is a string with
    a + as prefix.
    '''
    __metaclass__ = models.SubfieldBase
    empty_strings_allowed = False

    def __init__(self, verbose_name=None, name=None, blank=False, **kwargs):
        self.max_digits = 32
        self.decimal_places = 0
        super(PhoneNumberField, self).__init__(verbose_name, name, blank=blank,
                                               null=blank, **kwargs)

    def get_internal_type(self):
        return 'DecimalField'

    def to_python(self, value):
        if isinstance(value, basestring) or value is None:
            return value
        return '+%s' % value

    if django_version < (1, 2):
        def get_db_prep_value(self, value):
            return self.get_prep_value(value)

    def get_prep_value(self, value):
        if value is None:
            return None
        assert len(value) >= 2 and value[0] == '+', \
            'A PhoneNumberField will only store fully qualified numbers.'
        return value[1:]

    def formfield(self, **kwargs):
        defaults = {
            'form_class': fields.PhoneNumberField,
        }
        defaults.update(kwargs)
        return super(PhoneNumberField, self).formfield(**defaults)
