# vim: set ts=8 sw=4 sts=4 et ai:
from django.db import connection
try:
    from django.db.utils import DatabaseError, IntegrityError
except ImportError:  # Django 1.1-
    from django.db.backends.sqlite3.base import DatabaseError, IntegrityError
from osso.sequence.backends import (BaseSequence, SequenceDoesNotExist,
                                    SequenceError)


class Sequence(BaseSequence):
    """
    SQLite3 Sequence class
    """
    def lock(self, cursor):
        """
        Obtain an exclusive lock. This is reduced to a no-op.

        According to:
        - https://code.djangoproject.com/ticket/12118 sharing of the
          in-memory DB between threads is illegal
        - we use an in-memory DB for tests
        - the locking strategies as outlined in several places have
          unintented side-effects

        Django already locks the entire file when loading a DB upon
        connect, so we could probably do without this locking entirely.
        I think?
        """
        # On 2014-11-10 with sqlite3 3.8.2 and Django 1.1.4 the locking
        # mode is in "normal".
        #
        # Don't which to an exclusive lock like described here:
        #     http://www.mimec.org/node/306
        # This already "commits" the current work.
        #     cursor.execute("PRAGMA locking_mode = EXCLUSIVE")
        # And also doing this doesn't make it better.
        #     cursor.execute("BEGIN EXCLUSIVE")
        # By the way, we cannot do:
        #     cursor.execute('COMMIT')
        # because it yields a:
        #     sqlite3.OperationalError:
        #       cannot commit - no transaction is active
        # Not can we do this:
        #     connection._commit()  # ouch.. internals
        # It would COMMIT, but that breaks the rollback at the end of
        # the test cases.
        pass

    def unlock(self, cursor):
        """
        Release an exclusive lock.

        See notes in ``lock()``.
        """
        pass

    def create(self, name, start=1, increment=1):
        """
        Create a sequence with identifier ``name``.
        """
        self.validate_name(name)

        cursor = connection.cursor()
        self.lock(cursor)
        try:
            cursor.execute('INSERT INTO sequence_sequence '
                           '(name, start, increment) '
                           'VALUES (%s, %s, %s)',
                           (name, start, increment))
        except IntegrityError:
            raise SequenceError('sequence %r already exists' % name)
        finally:
            self.unlock(cursor)

    def drop(self, name):
        """
        Drop the sequence with identifier ``name`` if it exists.
        """
        self.validate_name(name)

        cursor = connection.cursor()
        self.lock(cursor)
        try:
            cursor2 = cursor.execute('DELETE FROM sequence_sequence '
                                     'WHERE name = %s',
                                     (name,))
            rowcount = cursor2.rowcount
        finally:
            self.unlock(cursor)

        if rowcount == 0:
            raise SequenceDoesNotExist('sequence %r does not exist' % name)

    def currval(self, name):
        """
        Return the current value of the sequence ``name``.
        """
        self.validate_name(name)

        cursor = connection.cursor()
        self.lock(cursor)
        try:
            cursor.execute('SELECT value FROM sequence_sequence '
                           'WHERE name = %s',
                           (name,))

            row = cursor.fetchone()
            if row is None:
                raise SequenceDoesNotExist('sequence %r does not exist' % name)
            if row[0] is None:
                raise SequenceError('sequence %r has no value' % name)
            value = row[0]
        finally:
            self.unlock(cursor)

        return value

    def nextval(self, name):
        """
        Return the next value for the sequence ``name``.
        """
        self.validate_name(name)

        cursor = connection.cursor()
        self.lock(cursor)
        try:
            cursor2 = cursor.execute('UPDATE sequence_sequence '
                                     'SET value = value + increment '
                                     'WHERE name = %s AND value IS NOT NULL',
                                     (name,))

            if cursor2.rowcount == 0:
                cursor2 = cursor.execute('UPDATE sequence_sequence '
                                         'SET value = start '
                                         'WHERE name = %s AND value IS NULL',
                                         (name,))

            cursor.execute('SELECT value FROM sequence_sequence '
                           'WHERE name = %s',
                           (name,))
            row = cursor.fetchone()
            if row is None:
                raise SequenceDoesNotExist('sequence %r does not exist' % name)

            value = row[0]
            assert value is not None
        finally:
            self.unlock(cursor)

        return value

    def setval(self, name, value):
        """
        Set the value for sequence ``name`` to ``value``.
        """
        self.validate_name(name)

        cursor = connection.cursor()
        self.lock(cursor)
        try:
            cursor2 = cursor.executemany('UPDATE sequence_sequence '
                                         'SET value = %s '
                                         'WHERE name = %s',
                                         [(value, name)])
            rowcount = cursor2.rowcount
        finally:
            self.unlock(cursor)

        if rowcount == 0:
            raise SequenceDoesNotExist('sequence %r does not exist' % name)

    def install(self, **kwargs):
        """
        Hook to prepare the database for sequences.
        """
        cursor = connection.cursor()
        self.lock(cursor)
        try:
            cursor.execute("""
                CREATE TABLE sequence_sequence (
                    name TEXT(63) NOT NULL,
                    start INTEGER NOT NULL,
                    increment INTEGER NOT NULL,
                    value INTEGER NULL,
                    PRIMARY KEY (name)
                )
            """)
        except DatabaseError:
            # Already exists?
            pass
        finally:
            self.unlock(cursor)
