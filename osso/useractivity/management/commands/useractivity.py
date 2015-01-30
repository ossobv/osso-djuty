# vim: set ts=8 sw=4 sts=4 et ai:
from osso.core.management.base import BaseCommand, CommandError
from osso.aboutconfig.utils import aboutconfig
from osso.useractivity import IDLE_MAX_DEFAULT, prune_idlers


class Command(BaseCommand):
    '''
    Run useractivity-related commands.
    '''
    help = '''Run useractivity-related commands.

Choose one of:
 * cleanup      Should be run periodically (every minute is fine) to prune
                idlers: automatically send logged_out signals for those
                users that are past the idle_max time defined in the
                useractivity.idle_max aboutconfig setting. Decrease
                verbosity to 0 when run as a cronjob.'''

    def get_version(self):
        return '1.0 initial'

    def handle(self, *args, **kwargs):
        if len(args) == 1 and args[0] == 'cleanup':
            self.cleanup(quiet=(int(kwargs['verbosity']) == 0))
        else:
            raise CommandError('Invalid arguments, see useractivity --help')

    def cleanup(self, quiet=False):
        idle_max = int(aboutconfig('useractivity.idle_max', IDLE_MAX_DEFAULT))
        assert idle_max >= 0

        if not quiet:
            print('Useractivity cleanup, running prune_idlers '
                  'with idle_max set to %d seconds.' % idle_max)

        pruned_users = prune_idlers(idle_max)
        if not quiet:
            print('Sent logout signal for %d logged on user(s): %s' %
                  (len(pruned_users),
                   ', '.join(i.username for i in pruned_users)))
