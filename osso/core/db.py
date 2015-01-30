# vim: set ts=8 sw=4 sts=4 et ai:
from django import VERSION as django_version
from django.conf import settings
from django.db import DatabaseError, connection, transaction
from django.db.transaction import commit_manually, commit_on_success


__all__ = ('suppressed_sql_notes', 'add_constraint', 'enumify')


class suppressed_sql_notes(object):
    '''
    Pimp a cursor object to suppress SQL notes and re-enable the
    original configuration when done.

    Use this in a with statement, like so:
      with suppressed_sql_notes(connection.cursor()) as cursor:
        cursor.execute('STUFF THAT YIELDS HARMLESS NOTICES')

    See django bug #12293 marked as WONTFIX.
    '''
    def __init__(self, cursor):
        self.cursor = cursor

    def __enter__(self):
        self.cursor.execute('''SET @OLD_SQL_NOTES=@@SQL_NOTES, SQL_NOTES=0;''')
        return self.cursora

    def __exit__(self, type, value, traceback):
        self.cursor.execute('''SET SQL_NOTES=@OLD_SQL_NOTES;''')


@commit_manually
def add_constraint(model, column, check):
    '''
    Add a simple constraint on a column.
    Use it from a post-syncdb hook, like:

    def f(sender=None, **kwargs):
        add_constraint(MyModel, 'mycolumn', '> 0')
    post_syncdb.connect(f, sender=sys.modules[__name__]) # alas, no __module__
    '''
    table = model._meta.db_table
    qn = connection.ops.quote_name
    qn_table = qn(table)
    qn_column = qn(column)
    qn_constraint = qn('%s_%s_check' % (table, column))

    if django_version < (1, 2):
        db_engine = settings.DATABASE_ENGINE
    else:
        db_engine = settings.DATABASES['default']['ENGINE']

    # The testing framework in django 1.3 calls syncdb and then
    # flush. This causes post_syncdb to be called for both
    # syncdb and the following flush call. The post_syncdb
    # documentation says:
    # """It is important that handlers of this signal perform
    # idempotent changes (e.g. no database alterations) as this
    # may cause the flush management command to fail if it also
    # ran during the syncdb command."""
    # The fix:
    # Make sure the ADD constraint is done safely (ignore it if
    # exists or remove if before creation).
    if db_engine in ('postgresql_psycopg2',
                     'django.db.backends.postgresql_psycopg2'):
        queries = (
            (True, ('ALTER TABLE %s DROP CONSTRAINT %s;' %
                    (qn_table, qn_constraint))),
            (False, ('ALTER TABLE %s ADD CONSTRAINT %s CHECK (%s %s);' %
                     (qn_table, qn_constraint, qn_column, check))),
        )
    else:
        raise NotImplementedError('add_constraint is not implemented for '
                                  'database engine %s' % db_engine)

    # Execute the queries
    cursor = connection.cursor()
    for may_fail, query in queries:
        try:
            cursor.execute(query)
        except DatabaseError:
            # constraint "xyz_abc" of relation "xyz" does not exist
            transaction.rollback()
            if not may_fail:
                raise
        else:
            transaction.commit()


@commit_on_success
def enumify(model, column, choices, null=False):
    '''
    Modify a table column to use ENUMs instead of strings for ChoiceFields.
    Use it from a post-syncdb hook, like:

    def f(sender=None, **kwargs):
        enumify(MyModel, 'mycolumn', (i[0] for i in MYCOLUMN_CHOICES))
    post_syncdb.connect(f, sender=sys.modules[__name__]) # alas, no __module__

    Note that alter statements may be tricky when you wish to revise your
    choices. Postgres example:
      -- change type back to varchar first
      ALTER TABLE sms_textmessage ALTER COLUMN status TYPE VARCHAR(15);
      -- drop and recreate the type with the new values
      DROP TYPE sms_textmessage_status_enum;
      CREATE TYPE sms_textmessage_status_enum AS
        ENUM ('in', 'rd', 'out', 'pnd', 'nak', 'ack');
      -- change the type back to the enum type with an explicit conversion
      ALTER TABLE sms_textmessage ALTER COLUMN status
        TYPE sms_textmessage_status_enum
        USING status::sms_textmessage_status_enum;
    '''
    table = model._meta.db_table
    choices = list(choices)  # now we can accept generators as well as lists
    placeholders_str = ', '.join('%s' for i in choices)
    qn = connection.ops.quote_name
    qn_table, qn_column = qn(table), qn(column)

    if django_version < (1, 2):
        db_engine = settings.DATABASE_ENGINE
        db_name = settings.DATABASE_NAME
    else:
        db_engine = settings.DATABASES['default']['ENGINE']
        db_name = settings.DATABASES['default']['NAME']

    # Check if it is done already. But only for MySQL since that ALTER TABLE
    # is blocking and slow. Postgres doesn't have an equally simple query to
    # find out whether it is done already. But I'm betting it detects that it
    # is and runs a lightning fast no-op.
    if db_engine in ('mysql', 'django.db.backends.mysql'):
        cursor = connection.cursor()
        cursor.execute('SELECT data_type, column_type, is_nullable FROM information_schema.columns '
                       'WHERE table_schema = %s AND table_name = %s AND column_name = %s',
                       (db_name, table, column))
        orig_datatype, orig_columntype, orig_isnull = cursor.fetchall()[0]
        if orig_datatype.lower() == 'enum' and ((orig_isnull.lower() != 'no') == null):
            # Is already an enum with same is_null properties.
            assert orig_columntype[0:6] == "enum('"
            assert orig_columntype[-2:] == "')"
            orig_choices = orig_columntype[6:-2]        # drop "enum('" and "')"
            orig_choices = orig_choices.split("','")    # split "abc','def','ghi"
            if set(orig_choices) == set(choices):
                # Same, do nothing.
                return
        del cursor

    # Prepare the queries
    if db_engine in ('mysql', 'django.db.backends.mysql'):
        queries = (
            ('ALTER TABLE %s CHANGE COLUMN %s %s ENUM(%s) %sNULL' %
             (qn_table, qn_column, qn_column, placeholders_str,
              ('NOT ', '')[null]), choices),
        )
    elif db_engine in ('postgresql_psycopg2',
                       'django.db.backends.postgresql_psycopg2'):
        qn_enum_type = qn('%s_%s_enum' % (table, column))

        # Do the create type separately as it may already exist (due
        # to a failed previous syncdb). We cannot do drop type if
        # exists here, as it cascade drops the column.
        from psycopg2 import ProgrammingError
        cursor = connection.cursor()
        try:
            cursor.execute(('CREATE TYPE %s AS ENUM(%s)' %
                            (qn_enum_type, placeholders_str)),
                           choices)
        except (DatabaseError, ProgrammingError):
            transaction.rollback()
        del cursor

        queries = (
            ('ALTER TABLE %s ALTER COLUMN %s TYPE %s USING %s::%s' %
             (qn_table, qn_column, qn_enum_type, qn_column, qn_enum_type),),
            ('ALTER TABLE %s ALTER COLUMN %s %s NOT NULL' %
             (qn_table, qn_column, ('SET', 'DROP')[null]),),
        )
    elif db_engine in ('sqlite3', 'django.db.backends.sqlite3'):
        # You didn't want any performance anyway, as you're using
        # sqlite.. We're done here.
        queries = ()
    else:
        raise NotImplementedError('enumify is not implemented for '
                                  'database engine %s' % db_engine)

    # Execute the queries
    cursor = connection.cursor()
    for query_with_args in queries:
        cursor.execute(*query_with_args)
