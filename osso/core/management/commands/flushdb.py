# vim: set ts=8 sw=4 sts=4 et ai:
from optparse import make_option
import sys

from django import VERSION as django_version
from django.core.management import call_command
from django.contrib.auth.models import Group, User
try:
    from django.db import DEFAULT_DB_ALIAS
except ImportError:
    DEFAULT_DB_ALIAS = 'default'
from osso.core.management import utils
from osso.core.management.base import BaseCommand, docstring


class Command(BaseCommand):
    __doc__ = help = docstring("""
    Flush the database and recreate it from scratch.

    Implementated by:
     * drop and recreate database
     * syncdb
     * superuser creation
     * config_data insertion
     * example_data insertion
     """)

    if not django_version < (1, 2):
        option_list = BaseCommand.option_list + (
            make_option(
                '--database', action='store', dest='database',
                default=DEFAULT_DB_ALIAS,
                help='Nominates a database to flush. '
                     'Defaults to the "default" database.'),
        )

    def handle(self, *args, **kwargs):
        answer = raw_input('Are you sure you want to flush/reset the db '
                           '[y/n] ? ')
        if answer.strip() != 'y':
            print('Aborted.')
            sys.exit(1)

        database = kwargs.get('database', DEFAULT_DB_ALIAS)

        sys.stdout.write('Dropping and recreating database ...')
        utils.recreatedb(database=database)
        sys.stdout.write('done\n')

        sys.stdout.write('Creating tables and more syncdb stuff ...')
        call_command('syncdb', interactive=False, verbosity=0,
                     database=database)
        sys.stdout.write('done\n')

        sys.stdout.write('Creating superuser automatically ...')
        username, password, email = self.autosu(database=database)
        sys.stdout.write('done (%s, %s, %s)\n' % (username, password, email))

        sys.stdout.write('Loading fixtures: config_data, example_data ...')
        call_command('loaddata', 'config_data', 'example_data',
                     interactive=False, verbosity=0, database=database)
        sys.stdout.write('done\n')

    def autosu(self, database=DEFAULT_DB_ALIAS):
        # Non-interactive superuser creation
        import os
        import socket
        try:
            import pwd
            username = pwd.getpwuid(os.getuid())[0].lower()
        except (AttributeError, ImportError):
            # Windows does not have getpwuid nor getuid
            username = os.getenv('USERNAME', 'nobody')

        name = username.capitalize()
        password = '%s2' % username
        email = '%s@%s' % (username, socket.getfqdn())
        if hasattr(User.objects, 'db_manager'):
            mgr = User.objects.db_manager(database)
        else:
            mgr = User.objects
        user = mgr.create_user(username, email, password)
        user.is_staff, user.is_active, user.is_superuser = True, True, True
        try:
            user.first_name, user.last_name = name.split(' ', 2)
        except ValueError:
            user.first_name = name
        user.save()

        # Hook the user up with all groups already available at the
        # moment. This might not be appropriate for all users of
        # flushdb. Wait and see ;)
        user.groups.add(*Group.objects.all())

        return username, password, email
