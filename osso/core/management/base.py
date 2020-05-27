# vim: set ts=8 sw=4 sts=4 et ai:
#
# BEWARE!
# When you use the BaseCommand you get an altered sys.stdout.
#
# DO NOT DO THIS ANYWHERE:
#   from sys import stdout; stdout.whatever()
#
# If you do, you'll have imported the *old* stdout. In certain cases
# destruction at the end of the python program will raise errors, like
# this:
#   close failed in file object destructor:
#   sys.excepthook is missing
#   lost sys.stderr
# This is probably caused by the double destruction of stdout after
# sys.stderr has been destroyed as well. To tackle this, we close
# sys.old_stdout immediately: now you'll get an error upon using
# plain stdout immediately.

# USE THIS ONLY IF YOU CANNOT USE Command.stdout:
#   import sys; sys.stdout.whatever()
# ALWAYS USE:
# class Command(BaseCommand):
#     def handle(self, *args, **kwargs):
#         self.stdout.write('utf8 unbuffered heaven')
#

import atexit
import sys
from os import fdopen

from django.core.management.base import BaseCommand as DjangoBaseCommand
from django.core.management.base import CommandError
from django.db import connections

__all__ = ['BaseCommand', 'CommandError', 'docstring']


class BaseCommand(DjangoBaseCommand):
    """
    The original BaseCommand patched to:
    - always set stdout to the currently selected locale and in
      unbuffered (auto-flushing) mode. This simplifies outputting busy
      messages and shell pipe usage.
    - have a cronbg() method which wraps your cron() method to run it
      in the background.
    """
    def execute(self, *args, **kwargs):
        # Force unbuffered stdout.
        if ('stdout' not in kwargs
                and getattr(sys.stdout, 'name', None) == '<stdout>'):
            # Reopen without line buffering.
            reopened = fdopen(sys.stdout.fileno(), 'w', 0)
            # Disable/break the old one (see comment at the top).
            sys.stdout.close()
            kwargs['stdout'] = sys.stdout = reopened

        atexit.register(_cleanup_connections)

        return super(BaseCommand, self).execute(*args, **kwargs)

    def get_version(self):
        """
        Supply a default 1.0 initial version. This is fine for most purposes.
        """
        return '1.0 initial'

    def cron(self, **kwargs):
        raise NotImplementedError()

    def cronbg(self, **kwargs):
        """
        Start the cron method, as a daemon, supplying background=True
        and quiet=True.

        If you have really critical parts in your cron jobs, you should
        wrap them in signal(SIG_IGN) and signal(SIG_DFL) calls. That
        will cause the signal to be ignored completely, so you may need
        to kill the job multiple times before hitting a point where the
        signal is DFL.

        UPDATE: Or you could use pysigset and wrap the block in a
        with suspended_signals() block!

        Additionally, you may want to add something like this, either
        here or in your cron() method.

            if (not settings.DEBUG and
                pwd.getpwuid(os.getuid()).pw_name != 'www-data'):
                # Make sure that we run as www-data so we can behave
                # like the webserver.
                os.setuid(pwd.getpwnam('www-data').pw_uid)
        """
        import traceback
        from django.core.mail import mail_admins

        try:
            from daemon import DaemonContext
        except ImportError:
            from ll.daemon import Daemon

            class DaemonContext:
                def __enter__(self):
                    Daemon().start()

                def __exit__(self):
                    pass

        with DaemonContext():
            module_name = self.__module__.rsplit('.', 1)[-1]
            try:
                self.cron(background=True, quiet=True)
            except (KeyboardInterrupt, SystemExit) as e:
                traceback_str = traceback.format_exc()

                # If this is one of the regular kill signals...
                if (isinstance(e, KeyboardInterrupt) or
                        e.args == (0,) or
                        e.args == ('Terminating on signal 15',)):
                    # ... then adjust our regular handling.
                    # If we're in the middle of a sleep, then we don't need to
                    # notify anyone.
                    if (traceback_str.find('\n    time.sleep(') != -1 or
                            traceback_str.find('\n    sleep(') != -1):
                        pass
                    # But if we weren't, we should supply the backtrace.
                    else:
                        mail_admins(
                            '%s cronbg stopped manually' % (module_name,),
                            traceback_str
                        )
                    # No more mailing below.
                    traceback_str = None
            except Exception as e:
                traceback_str = traceback.format_exc()
            else:
                # If cron() stopped by returning, we won't send any mail.
                traceback_str = None

            if traceback_str:
                mail_admins(
                    'Exception in %s cronbg!' % (module_name,),
                    traceback.format_exc()
                )
                sys.exit(1)


def docstring(doc):
    """
    Trim string so docstring indentation is removed.
    """
    if not doc:
        return ''
    if doc[0] != '\n':
        raise NotImplementedError('FIXME: Expected docstring to start on '
                                  'second line, got this: %r' % (doc,))
    offset = 1
    while doc[offset] == ' ':
        offset += 1
    spacing = '\n' + ((offset - 1) * ' ')

    doc = doc.replace(spacing, '\n')
    return doc.strip()  # drop leading and trailing space (esp. the first LF)


def _cleanup_connections(*args, **kwargs):
    """
    If we don't run this at exit, we get lots of ugly postgres errors
    in the logs:

    2015-01-19 12:09:02 LOG:  could not receive data from client:
                              Connection reset by peer
    2015-01-19 12:09:02 LOG:  unexpected EOF on client connection
                              with an open transaction
    """
    for conn in connections:
        connections[conn].close()
