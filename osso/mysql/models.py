# vim: set ts=8 sw=4 sts=4 et ai:
from base64 import b64decode, b64encode

from django import VERSION as django_version
from django.conf import settings
from django.db import models
from django.utils.translation import ugettext_lazy as _

try:
    from django.utils.six import with_metaclass
except ImportError:
    def with_metaclass(meta, superclass):
        return superclass


def _db_engines():
    if django_version >= (1, 2):
        engines = set(i['ENGINE'].rsplit('.', 1)[-1]
                      for i in settings.DATABASES.values())
    else:
        engines = set([settings.DATABASE_ENGINE])
    return engines


_is_mysql = all(i == 'mysql' for i in _db_engines())

if not _is_mysql:
    from warnings import warn
    warn('Not using MySQL engine, AsciiField substring match becomes case '
         'sensitive (SQLite) and BlobField will suffer poor performance, '
         'broken substring search and you cannot rely on the SQL LENGTH() '
         'function.')


class AsciiField(models.CharField):
    """
    MySQL-only ASCII field. If you want to use a different DB, check if
    this still works over there.

    Please run the Django unit tests to see if it works as advertised.
    """
    description = _('ASCII string (up to %(max_length)s)')

    def get_prep_value(self, value):
        if value is None:
            return None
        # In python3 we will treat this as unicode.  But we make sure
        # that any non-ascii is removed.
        return value.encode('ascii', 'replace').decode('ascii')

    def db_type(self, connection=None):
        # Newer Djangos pass connection parameter. Django 1.1 does not.
        if connection and connection.vendor == 'mysql':
            return ('VARCHAR(%s) CHARACTER SET ascii '
                    'COLLATE ascii_bin' %
                    (self.max_length,))
        elif connection:
            return 'VARCHAR(%s)' % (self.max_length,)
        elif _is_mysql:
            return ('VARCHAR(%s) CHARACTER SET ascii '
                    'COLLATE ascii_bin' %
                    (self.max_length,))
        else:
            return 'VARCHAR(%s)' % (self.max_length,)

    if django_version < (1, 2):
        def get_db_prep_value(self, value):
            return self.get_prep_value(value)


class BlobField(with_metaclass(models.SubfieldBase, models.Field)):
    """
    MySQL blob/binary field. Please run the accompanying tests.
    """
    description = 'Binary'

    # For the MySQL version we don't need this. The to_python and
    # value_to_string methods will get called for serializing and
    # deserializing fixtures only.
    # For the SQLite3 version, we store the values in base64 in the DB,
    # so to_python must always get called.
    if not _is_mysql:
        __metaclass__ = models.SubfieldBase

        def to_python(self, value):
            """
            Differentiates between unicode and binary strings. If it's
            unicode it comes from the DB or a fixture.
            """
            if value is None:
                return None
            if not isinstance(value, bytes):
                value = b64decode(value)
            return bytes(value)

        def value_to_string(self, obj):
            """
            Return unicode to flag that we're dealing with serialized data.
            """
            value = self._get_val_from_obj(obj)
            return unicode(b64encode(value))

    if _is_mysql:
        def db_type(self, connection=None):
            # We use a LONGBLOB which can hold up to 4GB of bytes. A
            # MEDIUMBLOB of max 16MB should probably be enough, but we
            # don't want to add an arbitrary limit there.
            return 'LONGBLOB'
    else:
        def get_prep_value(self, value):
            if value is None:
                return None
            if not isinstance(value, bytes):
                value = value.encode('utf-8')
            return b64encode(value).decode('ascii')  # unicode

        def db_type(self, connection=None):
            return 'BLOB'

        if django_version < (1, 2):
            def get_db_prep_value(self, value):
                return self.get_prep_value(value)

    def get_db_prep_lookup(self, lookup_type, value, **kwargs):
        if lookup_type not in ('isnull',):
            raise TypeError('Lookup type %s is not supported.' % lookup_type)
        return super(BlobField, self).get_db_prep_lookup(lookup_type, value)
