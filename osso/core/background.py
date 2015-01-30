# vim: set ts=8 sw=4 sts=4 et ai:
import os
import resource


__all__ = ('disowned',)


MAXFD = resource.getrlimit(resource.RLIMIT_NOFILE)[1]  # = highest_fd + 1
if MAXFD == resource.RLIMIT_NOFILE:
    MAXFD = 2048


def disowned(*command_and_args):
    """
    Start subprocess and disown. This is the better alternative to simply
    calling subprocess.Popen() and ignoring the result, because this ensures
    that (a) the process doesn't die when the parent gets killed, and (b) it
    is reaped by init when done (instead of relying on python garbage
    collection).

    It preserves the parent environment, because that's the common scenario.
    """
    # First fork.
    pid = os.fork()
    if pid:
        # Reap the zombie by fetching the return value. The second fork ensures
        # that that's quick.
        os.waitpid(pid, 0)
        return

    # For a process to be truly daemonized (ran in the background) we should
    # ensure that the session leader is killed so that there is no possibility
    # of the session ever taking control of the TTY.
    os.setsid()

    # Second fork, do it as soon as possible.
    if os.fork():
        os._exit(0)

    # Begin cleanup after ourselves. Start by releasing mount points / dirs.
    os.chdir('/')

    # Close all open files.
    # OBSERVE: we do not need to re-open stdout/stderr to /dev/null.
    # The following works without hassle on python 2.7.
    # >>> import os, sys
    # >>> os.close(2)
    # >>> sys.stderr.write(LOTS_OF_DATA)
    try:
        os.closerange  # exists since python 2.6
    except AttributeError:
        for fd in xrange(MAXFD - 1, -1, -1):
            try:
                os.close(fd)
            except OSError:
                pass
    else:
        os.closerange(0, MAXFD)

    # Turn into the requested process.
    os.execve(command_and_args[0], command_and_args, os.environ)
