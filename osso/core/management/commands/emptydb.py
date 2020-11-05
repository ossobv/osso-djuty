# vim: set ts=8 sw=4 sts=4 et ai:
import sys

from osso.core.management import utils
from osso.core.management.base import BaseCommand, docstring


class Command(BaseCommand):
    __doc__ = help = docstring("""
    Create/recreate the database and leave it empty.
    """)

    def handle(self, *args, **kwargs):
        answer = input('Are you sure you want to create/empty the db '
                           '[y/n] ? ')
        if answer.strip() != 'y':
            print('Aborted.')
            sys.exit(1)

        sys.stdout.write('Dropping and recreating database ...')
        utils.recreatedb()
        sys.stdout.write('done\n')
