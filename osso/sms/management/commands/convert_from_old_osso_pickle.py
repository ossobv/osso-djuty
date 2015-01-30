# vim: set ts=8 sw=4 sts=4 et ai:
import sys

from osso.core import pickle
from osso.core.management.base import BaseCommand, CommandError
from osso.sms.models import TextMessage


class Command(BaseCommand):
    '''
    Convert the old osso.core.pickle cescape pickled sms_textmessage
    metadata to the "current" pickle data type (not defined here).
    '''
    help = '''Convert the old osso.core.pickle cescape pickled sms_textmessage
    metadata to the "current" pickle data type (not defined here).'''

    def handle(self, *args, **kwargs):
        if len(args):
            raise CommandError('This command takes no arguments.')

        quiet = int(kwargs['verbosity']) == 0
        block_size = 100

        if not quiet:
            total = float(TextMessage.objects.count())
            processed = 0

        first_id = -1
        while True:
            msgs = (TextMessage.objects.filter(id__gt=first_id)
                    .order_by('id')[0:block_size])
            msg = None
            for msg in msgs:
                if msg.metadata != '':
                    data = pickle.loadascii(msg.metadata)
                    msg.meta = data
                    msg.save()

            if not quiet:
                processed += block_size
                sys.stdout.write('\r%d%%' % (processed / total * 100))

            if not msg:
                break
            first_id = msg.id

        if not quiet:
            print('\rdone')
