# vim: set ts=8 sw=4 sts=4 et ai:
# The MySQLdb.OperationalError is superseded by the django DatabaseError
# in Django 1.4+.
import warnings
from MySQLdb import IntegrityError, OperationalError

from django.db import (DatabaseError, IntegrityError as DjangoIntegrityError,
                       connection, transaction)
from osso.sequence.backends import (BaseSequence, SequenceDoesNotExist,
                                    SequenceError)


class Sequence(BaseSequence):
    '''
    MySQL Sequence class
    '''
    def create(self, name, start=1, increment=1):
        '''
        Create a sequence with identifier `name`
        '''
        self.validate_name(name)
        cursor = connection.cursor()

        sid = transaction.savepoint()
        try:
            cursor.execute('INSERT INTO sequence_sequence '
                           '(`name`, `start`, `increment`) '
                           'VALUES (%s, %s, %s)',
                           (name, start, increment))
        except (IntegrityError, DjangoIntegrityError) as e:
            transaction.savepoint_rollback(sid)
            # In older Django (1.1-ish) we get a MySQL exception. In newer
            # versions, we get a Django-wrapped one.
            if e.args[0] == 1062:  # duplicate key
                raise SequenceError('sequence %r already exists' % name)
            raise
        else:
            transaction.savepoint_commit(sid)

    def drop(self, name):
        '''
        Drop the sequence with identifier `name` if it exists
        '''
        self.validate_name(name)
        cursor = connection.cursor()
        rows = cursor.execute('DELETE FROM sequence_sequence WHERE name = %s',
                              (name,))
        if rows == 0:
            raise SequenceDoesNotExist('sequence %r does not exist' % name)

    def currval(self, name):
        '''
        Return the current value of the sequence `name`
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
        return row[0]

    def nextval(self, name):
        '''
        Return the next value for the sequence `name`
        '''
        self.validate_name(name)
        cursor = connection.cursor()
        try:
            # The new way. We're using a stored prodecure nowadays
            # instead of a function, because the function does not
            # guarantee proper replication. The SP will get split up
            # into separate statements. See:
            # http://dev.mysql.com/doc/refman/5.1/en/ \
            #        stored-programs-logging.html
            cursor.callproc('nextval', (name,))
        except (DatabaseError, OperationalError):  # SP does not exist
            # The old way
            cursor.execute('SELECT nextval(%s)',
                           (name,))
            row = cursor.fetchone()
        else:
            row = cursor.fetchone()
            discard = cursor.nextset()  # must call nextset for SP
            assert discard == 1

        if row is None or row[0] is None:
            raise SequenceDoesNotExist('sequence %r does not exist' % name)
        return row[0]

    def setval(self, name, value):
        '''
        Set the value for sequence `name` to `value`
        '''
        self.validate_name(name)
        cursor = connection.cursor()
        rows = cursor.execute('UPDATE sequence_sequence SET value = %s '
                              'WHERE name = %s',
                              (value, name))
        if rows == 0:
            raise SequenceDoesNotExist('sequence %r does not exist' % name)

    def install(self, **kwargs):
        '''
        Hook to prepare the database for sequences
        '''
        cursor = connection.cursor()
        try:
            cursor.execute('''
                CREATE TABLE sequence_sequence (
                    `name` VARCHAR(63) character set ascii
                                       collate ascii_bin NOT NULL,
                    `start` INTEGER NOT NULL,
                    `increment` INTEGER NOT NULL,
                    `value` INTEGER NULL,
                    PRIMARY KEY (`name`)
                );
            ''')
        except (DatabaseError, OperationalError) as e:
            if e.args[0] != 1050:  # table exists
                raise
        try:
            # cursor.execute('''
            #     CREATE FUNCTION nextval(seq_name VARCHAR(63))
            #         RETURNS INT
            #         MODIFIES SQL DATA
            #         SQL SECURITY INVOKER
            #     BEGIN
            #         UPDATE sequence_sequence
            #             SET value = LAST_INSERT_ID(
            #                     COALESCE(value + increment, start))
            #             WHERE name = seq_name;
            #         IF ROW_COUNT() = 0 THEN
            #             RETURN NULL;
            #         END IF;
            #         RETURN LAST_INSERT_ID();
            #     END
            # ''')
            cursor.execute('''
                CREATE PROCEDURE `nextval`(IN seq_name VARCHAR(63)
                                           CHARACTER SET ascii)
                    MODIFIES SQL DATA
                    SQL SECURITY INVOKER
                BEGIN
                    UPDATE sequence_sequence
                        SET value = LAST_INSERT_ID(COALESCE(value + increment,
                                                            start))
                        WHERE name = seq_name;
                    IF ROW_COUNT() = 0 THEN
                        SELECT NULL;
                    ELSE
                        SELECT LAST_INSERT_ID();
                    END IF;
                END
            '''.replace('\n                ', '\n').strip())
        except (DatabaseError, OperationalError) as e:
            if e.args[0] == 1304:  # function/procedure exists
                pass
            # elif e.args[0] == 1418: # ... this function has none of
            #                         #     DETERMINISTIC, NO SQL, etc..
            #     # Add the function by hand with an account with more powers
            #     print('****************************************************')
            #     print('WARNING: fail adding nextval func. in %s' % __file__)
            #     print('****************************************************')
            else:
                raise

    def has_savepoint_issues(self):
        if not hasattr(self, '_has_savepoint_issues'):
            try:
                # Check whether we're using ndbcluster. Because if we are,
                # we cannot use savepoints, even if we wanted to in
                # testcases.
                #   <Svedrin> I'm using Django on an NDB (mysql) cluster.
                #   since I updated to Django 1.4, I get the error: "The
                #   storage engine for the table doesn't support SAVEPOINT"
                #   <Svedrin> is there a config option or something to
                #   disable savepoints?
                # and
                #   https://bugs.launchpad.net/pbxt/+bug/720894
                cursor = connection.cursor()
                cursor.execute('SELECT @@default_storage_engine;')
                data = cursor.fetchall()
                self._has_savepoint_issues = (data[0][0] == 'ndbcluster')
                del data
            except:
                # Fallback, in case there is no @@default_storage_engine.
                self._has_savepoint_issues = False
            else:
                if self._has_savepoint_issues:
                    # Because we cannot use savepoints *and* mysql
                    # duplicate insert rolls back the transaction,
                    # our test case gets into a zeroed out state.
                    # At that point, there is no use in trying to
                    # continue with the test.
                    #
                    # For normal operations, where autocommit=1, we
                    # have no problems.
                    warnings.warn(
                        "watch out, we skip a few tests because ndbcluster "
                        "rolls back after an integrity error, so we "
                        "we get the worst between MyISAM and InnoDB")

        return self._has_savepoint_issues
