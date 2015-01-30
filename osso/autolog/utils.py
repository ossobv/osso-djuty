# vim: set ts=8 sw=4 sts=4 et ai:
from datetime import date
from time import strftime
from os import getpid, path, rename, stat, unlink
from threading import currentThread

from osso.core.fileutil import select_writable_path
from osso.aboutconfig.utils import aboutconfig


def _logpath():
    '''
    Returns the logging path as defined in the aboutconfig autolog.path
    setting. The autolog.path setting is a colon-delimited list of paths
    to try. The paths are tried from left to right, if the path is
    relative it is relative to the first path found in the PYTHONPATH
    environment variable or the "current directory" if that path is
    empty.

    If the path does not exist, _logpath attempts to create it. First
    when that fails it moves on to the next path.
    '''
    pathstr = select_writable_path(aboutconfig('autolog.path').split(':'))
    assert pathstr is not None, ('No usable logging path found in '
                                 'autolog.path setting!')
    return pathstr


def _logrotate(filename):
    '''
    Rotate the log if its modification time is not today.
    Keep at most 7 log files.
    '''
    max = 30
    try:
        statinfo = stat(filename)
    except OSError:
        return False

    if date.today() != date.fromtimestamp(statinfo.st_mtime):
        try:
            unlink('%s.%i' % (filename, max - 1))
        except OSError:
            pass
        for i in range(max - 2, 0, -1):
            try:
                rename('%s.%i' % (filename, i), '%s.%i' % (filename, i + 1))
            except OSError:
                pass
        rename('%s' % filename, '%s.1' % filename)  # don't catch error here
    return True


NAMEDIDS = ('apple', 'block', 'color', 'death', 'entry',
            'focus', 'green', 'hotel', 'infra', 'jacob',
            'kebab', 'looks', 'mafia')


def log(message, log='main', subsys='(main)', fail_silently=True):
    '''
    Writes a log message to the log file named log. It uses the
    aboutconfig autolog.path variable to find a usable path.

    If fail_silently is set, no exception is raised when no valid log
    path could be found. This is on by default. If writing to the log
    should fail, you get still get raised errors.
    '''
    try:
        filename = path.join(_logpath(), '%s.log' % log)
    except AssertionError:
        if fail_silently:
            return
        raise
    _logrotate(filename)
    datestr = strftime('%Y-%m-%d %H:%M:%S%z')
    pid, tid = getpid(), currentThread().ident
    uniqueid = '%04x%012x' % (pid, tid)
    namedid = (pid + tid) % 13
    prefix = '%s: [%s:%s:%s]' % (datestr, uniqueid[:8], uniqueid[8:],
                                 NAMEDIDS[namedid])

    try:
        line = (u'%s %s: %s\n' % (prefix, subsys, message)).encode('utf-8')
    except UnicodeDecodeError:
        line = ('%s %s: %s\n' % (prefix, subsys, message))
    assert isinstance(line, str)

    f = None
    try:
        f = open(filename, 'a')
        f.write(line)
    except IOError:
        if fail_silently:
            return
        raise
    finally:
        if f:
            f.close()
