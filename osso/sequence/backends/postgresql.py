# vim: set ts=8 sw=4 sts=4 et ai:
from functools import wraps

from django.db import DatabaseError, connection, transaction
from osso.sequence.backends import (BaseSequence, SequenceDoesNotExist,
                                    SequenceError)


def savepoint(func):
    """
    After a "relation does not exist" failure, the current transaction
    is aborted. This decorator makes sure we can continue.
    """
    @wraps(func)
    def wrapper(*args, **kwargs):
        sid = transaction.savepoint()
        try:
            ret = func(*args, **kwargs)
        except:
            transaction.savepoint_rollback(sid)
            raise
        transaction.savepoint_commit(sid)
        return ret
    return wrapper


class Sequence(BaseSequence):
    """
    PostgreSQL Sequence class
    """
    def seqname(self, name):
        # http://www.postgresql.org/docs/9.3/static/sql-syntax-lexical.html\
        #   #SQL-SYNTAX-IDENTIFIERS
        # > The system uses no more than NAMEDATALEN-1 bytes of an
        # > identifier; longer names can be written in commands, but
        # > they will be truncated. By default, NAMEDATALEN is 64 so
        # > the maximum identifier length is 63 bytes.
        # Ergo, we make the prefix as short as possible.
        #
        # NOTE: We could override validate_name to throw an error if
        # the size exceeds 60 (because we add 3), but if your custom
        # postgresql install has fixed the 63 character limit, we don't
        # want to create unjust limits. (And, this used to be 31
        # characters in the past, so we won't catch all problems
        # anyway.)
        return '_sq%s' % (name,)

    def seqname2(self, name):
        return '\'"%s"\'::text' % (self.seqname(name),)

    @savepoint
    def create(self, name, start=1, increment=1):
        '''
        Create a sequence with identifier `name`
        '''
        self.validate_name(name)
        cursor = connection.cursor()
        try:
            cursor.execute('CREATE SEQUENCE "%s" '
                           'INCREMENT %%s START %%s' % (self.seqname(name),),
                           (increment, start))
        except DatabaseError:
            raise SequenceError('sequence %r already exists' % name)

    @savepoint
    def drop(self, name):
        '''
        Drop the sequence with identifier `name` if it exists
        '''
        self.validate_name(name)
        cursor = connection.cursor()
        try:
            cursor.execute('DROP SEQUENCE "%s"' % (self.seqname(name),))
        except DatabaseError:
            raise SequenceDoesNotExist('sequence %r does not exist' % name)

    @savepoint
    def currval(self, name):
        '''
        Return the current value of the sequence `name`
        '''
        self.validate_name(name)
        cursor = connection.cursor()
        try:
            cursor.execute('SELECT last_value, is_called from "%s"' %
                           (self.seqname(name),))
        except DatabaseError:
            raise SequenceDoesNotExist('sequence %r does not exist' % name)
        value, is_called = cursor.fetchone()
        if not is_called:
            raise SequenceError('sequence %r has no value' % name)
        assert isinstance(value, int)
        return value

    @savepoint
    def nextval(self, name):
        '''
        Return the next value for the sequence `name`
        '''
        self.validate_name(name)
        cursor = connection.cursor()
        try:
            cursor.execute('SELECT nextval(%s)' % (self.seqname2(name),))
        except DatabaseError:
            raise SequenceDoesNotExist('sequence %r does not exist' % name)
        row = cursor.fetchone()
        assert isinstance(row[0], int)
        return row[0]

    @savepoint
    def setval(self, name, value):
        '''
        Set the value for sequence `name` to `value`
        '''
        self.validate_name(name)
        cursor = connection.cursor()
        try:
            cursor.execute('SELECT setval(%s, %s)' %
                           (self.seqname2(name), value))
        except DatabaseError:
            raise SequenceDoesNotExist('sequence %r does not exist' % name)

    def install(self, **kwargs):
        '''
        Hook to prepare the database for sequences
        '''
        pass
