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
        except Exception:
            transaction.savepoint_rollback(sid)
            raise
        transaction.savepoint_commit(sid)
        return ret
    return wrapper


class Sequence(BaseSequence):
    """
    PostgreSQL Sequence class
    """
    @savepoint
    def create(self, name, start=1, increment=1):
        '''
        Create a sequence with identifier "name"
        '''
        self.validate_name(name)
        cursor = connection.cursor()
        try:
            cursor.execute('INSERT INTO sequence_sequence '
                           '("name", "start", "increment") '
                           'VALUES (%s, %s, %s)',
                           (name, start, increment))
        except DatabaseError:
            raise SequenceError('sequence %r already exists' % name)

    @savepoint
    def drop(self, name):
        '''
        Drop the sequence with identifier "name" if it exists
        '''
        self.validate_name(name)
        cursor = connection.cursor()
        cursor.execute('DELETE FROM sequence_sequence WHERE name = %s',
                       (name,))
        if cursor.rowcount == 0:
            raise SequenceDoesNotExist('sequence %r does not exist' % name)

    @savepoint
    def currval(self, name):
        '''
        Return the current value of the sequence "name"
        '''
        self.validate_name(name)
        cursor = connection.cursor()
        cursor.execute('SELECT value FROM sequence_sequence WHERE name = %s',
                       (name,))
        row = cursor.fetchone()
        if row is None:
            raise SequenceDoesNotExist('sequence %r does not exist' % name)
        if row[0] is None:
            raise SequenceError('sequence %r has no value' % name)
        assert isinstance(row[0], int)
        return row[0]

    @savepoint
    def nextval(self, name):
        '''
        Return the next value for the sequence "name"
        '''
        self.validate_name(name)
        cursor = connection.cursor()
        try:
            cursor.execute(
                'UPDATE sequence_sequence '
                'SET value = COALESCE(value + increment, start) '
                'WHERE name = %s '
                'RETURNING value',
                (name,))
        except DatabaseError:
            raise SequenceDoesNotExist('sequence %r does not exist' % name)
        row = cursor.fetchone()
        if row is None:
            raise SequenceDoesNotExist('sequence %r does not exist' % name)
        assert isinstance(row[0], int)
        return row[0]

    @savepoint
    def setval(self, name, value):
        '''
        Set the value for sequence "name" to "value"
        '''
        self.validate_name(name)
        cursor = connection.cursor()
        cursor.execute('UPDATE sequence_sequence SET value = %s '
                       'WHERE name = %s',
                       (value, name))
        if cursor.rowcount == 0:
            raise SequenceDoesNotExist('sequence %r does not exist' % name)
