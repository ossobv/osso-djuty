# vim: set ts=8 sw=4 sts=4 et ai:
import os

from django.db import connections, DEFAULT_DB_ALIAS


def recreatedb(database=DEFAULT_DB_ALIAS):
    '''
    Drop and recreate the database.
    '''
    connection = connections[database]
    db_vendor = connection.vendor
    db_name = connection.settings_dict['NAME']

    # The MySQL case is simple. We drop the db, create the db and finally
    # select it.
    if db_vendor == 'mysql':
        cursor = connection.cursor()
        cursor.execute(
            'DROP DATABASE IF EXISTS `%(db)s`; '
            'CREATE DATABASE `%(db)s` %(encargs)s; USE `%(db)s`' % {
                'db': db_name,
                'encargs': ('DEFAULT CHARACTER SET utf8 '
                            'DEFAULT COLLATE utf8_unicode_ci')})
        cursor.close()

    # Postgres doesn't allow the database to be dropped while we're using it.
    elif db_vendor == 'postgresql':
        # We close the connection first. It gets reopened on demand.
        connection.close()

        connection.settings_dict['NAME'] = 'postgres'

        cursor = connection.cursor()
        connection.connection.set_isolation_level(0)
        dict = {'db': db_name, 'encargs': 'ENCODING = \'UTF8\''}
        cursor.execute('DROP DATABASE IF EXISTS "%(db)s";' % dict)
        cursor.execute('CREATE DATABASE "%(db)s" %(encargs)s;' % dict)
        cursor.close()
        connection.close()

        connection.settings_dict['NAME'] = db_name

    elif db_vendor == 'sqlite':
        # Do some extra checks to ensure that we're not doing something
        # really stupid.
        try:
            db = open(db_name, 'rb')
        except IOError:
            # No file? Nothing to do.
            pass
        else:
            try:
                header = db.read(16)
                if header != b'SQLite format 3\x00':
                    raise ValueError('Not an SQLite 3 database', db_name)
            finally:
                db.close()
            # Remove it
            os.unlink(db_name)

    else:
        raise NotImplementedError(
            'Drop/create for database type %s not implemented' % db_vendor)
