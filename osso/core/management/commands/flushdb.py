# vim: set ts=8 sw=4 sts=4 et ai:
import argparse
import optparse
import os
import pwd
import socket
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

    Implemented by:
     * drop and recreate database
     * syncdb
     * superuser creation
     * config_data insertion
     * example_data insertion
     """)
    # Optparse was used up to Django 1.8.
    if django_version < (1, 8):
        option_list = BaseCommand.option_list + (
            optparse.make_option(
                '--database', action='store', dest='database',
                default=DEFAULT_DB_ALIAS,
                help='Nominates a database to flush. '
                     'Defaults to the "default" database.'),
        )

    def add_arguments(self, parser):
        parser.formatter_class = argparse.RawTextHelpFormatter
        parser.add_argument(
            '--database', action='store', default='default', help=(
                'Nominates a database to flush. '
                'Defaults to the "default" database.'))

    def handle(self, *args, **kwargs):
        answer = raw_input(
            'Are you sure you want to flush/reset the db [y/n] ? ')
        if answer.strip() != 'y':
            self.stdout.write('Aborted.')
            sys.exit(1)

        database = kwargs.get('database', DEFAULT_DB_ALIAS)

        self.stdout.write('Dropping and recreating database ...', ending='')
        utils.recreatedb(database=database)
        self.stdout.write('done')

        self.stdout.write(
            'Creating tables and more migrate stuff ...', ending='')
        migrate_cmd = ('syncdb', 'migrate')[django_version >= (1, 7)]
        call_command(migrate_cmd, interactive=False, verbosity=0,
                     database=database)
        if migrate_cmd == 'migrate':
            # We'll need to do the initial_data manually too..
            call_command('loaddata', 'initial_data',
                         interactive=False, verbosity=0, database=database)
        self.stdout.write('done\n')

        self.stdout.write('Creating superuser automatically ...', ending='')
        username, password, email = self.autosu(database=database)
        self.stdout.write('done (%s, %s, %s)' % (username, password, email))

        self.stdout.write('Loading fixtures: config_data, example_data ...',
                          ending='')
        call_command('loaddata', 'config_data', 'example_data',
                     interactive=False, verbosity=0, database=database)
        self.stdout.write('done')

    def autosu(self, database=DEFAULT_DB_ALIAS):
        # Non-interactive superuser creation
        try:
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
