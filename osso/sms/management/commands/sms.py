# vim: set ts=8 sw=4 sts=4 et ai:
import sys

from osso.core.management.base import BaseCommand, CommandError
from osso.sms.models import TextMessage


class Command(BaseCommand):
    '''
    Run sms-related commands.
    '''
    help = '''Run sms-related commands.

Choose one of:
 * fixremoteop  Set the remote_operator field for outbound messages
                that do not have said field set. Usually all outbound
                messages have at least one inbound message that trigger
                these messages. This inbound message normally has an
                operator set. We use that data to populate the operator
                field in the outbound messages. Decrease verbosity to 0
                when run as a cron job.
 * sendlazy     Send all text messages that are in state outbound
                unsent. Any necessary send arguments are stored in the
                text message extra table (and possibly some backend
                specific options in the metadata). (The 'lazy' refers to
                the fact that it wasn't sent from the creating thread
                but is left to us to do the job.)'''

    def get_version(self):
        return '1.0 initial'

    def handle(self, *args, **kwargs):
        if len(args) == 1 and args[0] in ('fixremoteop', 'sendlazy'):
            getattr(self, args[0])(quiet=(int(kwargs['verbosity']) == 0))
        else:
            raise CommandError('Invalid arguments, see sms --help')

    def fixremoteop(self, quiet=False):
        # Broadcast messages do not get the remote_operator field set
        # automatically run this to set them afterwards.
        first_id = -1
        while True:
            new = list(TextMessage.objects.exclude(status__in=('in', 'rd'))
                       .filter(id__gt=first_id, remote_operator=None)
                       .order_by('id')[0:1])
            if len(new) == 0:
                break

            new = new[0]
            old = list(TextMessage.objects
                       .filter(remote_address=new.remote_address,
                               id__lt=new.id)
                       .exclude(remote_operator=None)
                       .order_by('-id')[0:1])
            if len(old) == 0:
                sys.stderr.write('No older inbound message found for '
                                 'outbound SMS %d.\n' % new.id)
            else:
                old = old[0]
                if not quiet:
                    print('Updating SMS %d with operator %s.' %
                          (new.id, old.remote_operator))
                new.remote_operator = old.remote_operator
                new.save()

            first_id = new.id

    def sendlazy(self, quiet=False):
        # Process all messages in the right order, and delaying the
        # destinations that fail. We expect the sms service to either
        # work or fail completely. The message content/parameters
        # shouldn't be to blame.
        #
        # This is a really simple version of a dequeueing cron job. If
        # you're doing serious SMS business, you'll probably want to
        # write your own.
        skip_destinations = []
        while True:
            msg = list(TextMessage.objects.filter(status='out')
                       .exclude(remote_address__in=skip_destinations)
                       .order_by('id')[0:1])
            if len(msg) == 0:
                break

            msg = msg[0]
            if not quiet:
                print('Selecting message %d to send (created %s)...' %
                      (msg.id, msg.created))

            # XXX: we could get the arguments from TextMessageExtra here
            # to supply to send(), or we can obsolete those parameters
            # and have the backend look up what it needs (see
            # sms_mollie2)

            try:
                msg.send()
            except Exception as e:
                if quiet:
                    raise
                print('Got exception (dst %s):' % (msg.remote_address,))
                print(e)
                skip_destinations.append(msg.remote_address)
