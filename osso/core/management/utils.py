# vim: set ts=8 sw=4 sts=4 et ai:
import re, os, subprocess
from django import VERSION as django_version
from django.conf import settings
try:
    from django.db import connections, DEFAULT_DB_ALIAS
except ImportError:
    from django.db import connection as real_connection
    DEFAULT_DB_ALIAS = 'default'
    connections = {DEFAULT_DB_ALIAS: real_connection}


def recreatedb(database=DEFAULT_DB_ALIAS):
    '''
    Drop and recreate the database.
    '''
    # >django-1.0 keeps the database settings in the connection object
    connection = connections[database]
    settings_prefix = 'DATABASE_'
    if django_version < (1, 2):
        db_engine = settings.DATABASE_ENGINE
        db_name = settings.DATABASE_NAME
    else:
        settings_prefix = ''
        db_engine = connection.settings_dict['ENGINE']
        db_name = connection.settings_dict['NAME']

    # The MySQL case is simple. We drop the db, create the db and finally
    # select it.
    if db_engine[-5:] == 'mysql':
        cursor = connection.cursor()
        cursor.execute('DROP DATABASE IF EXISTS `%(db)s`; CREATE DATABASE `%(db)s` %(encargs)s; USE `%(db)s`' % {
            'db': db_name,
            'encargs': 'DEFAULT CHARACTER SET utf8 DEFAULT COLLATE utf8_unicode_ci',
        })
        cursor.close()

    # Postgres doesn't allow the database to be dropped while we're using it.
    elif db_engine[-8:] in ('postgres', 'psycopg2'):
        # We close the connection first. It gets reopened on demand.
        connection.close()

        if django_version < (1, 1):
            settings.DATABASE_NAME = 'postgres'
        else:
            connection.settings_dict['%sNAME' % settings_prefix] = 'postgres'

        cursor = connection.cursor()
        connection.connection.set_isolation_level(0)
        dict = {'db': db_name, 'encargs': 'ENCODING = \'UTF8\''}
        cursor.execute('DROP DATABASE IF EXISTS "%(db)s";' % dict)
        cursor.execute('CREATE DATABASE "%(db)s" %(encargs)s;' % dict)
        cursor.close()
        connection.close()

        if django_version < (1, 1):
            settings.DATABASE_NAME = db_name
        else:
            connection.settings_dict['%sNAME' % settings_prefix] = db_name

    elif db_engine[-7:] == 'sqlite3':
        # Do some extra checks to ensure that we're not doing something
        # really stupid.
        try:
            db = open(db_name)
        except IOError:
            # No file? Nothing to do.
            pass
        else:
            header = db.read(16)
            if header != 'SQLite format 3\x00':
                raise ValueError('Not an SQLite 3 database', db_name)
            db.close()
            # Remove it
            os.unlink(db_name)

    elif db_engine == 'django_mongodb_engine':
        if re.search(r'[ .$/\\\0]', db_name):
            raise NotImplementedError('Database name contains illegal characters')

        # There is no mongo cursor right now, so this is probably the
        # correct way to do this.
        proc = subprocess.Popen(['mongo', db_name, '--quiet', '--eval', 'db.dropDatabase()'], stderr=subprocess.PIPE, stdout=subprocess.PIPE)
        proc.communicate()
        if proc.wait() != 0:
            raise ValueError('Dropping database %s failed!' % (db_name,))

    else:
        raise NotImplementedError('Drop/create for database type %s not implemented' % db_engine)
