# vim: set ts=8 sw=4 sts=4 et ai:
'''
NOTE: As this might get used very early on in the django settings file, you'll
want to avoid importing any django-specific module.
'''
import os
import pwd  # WTF? ``from pwd import getpwuid`` breaks tests??
import re
import stat
from datetime import datetime, timedelta
from subprocess import Popen, PIPE
from sys import modules
from tempfile import mkstemp


__all__ = ('import_module', 'ascii_filename', 'assert_writable',
           'file_needs_updating', 'safe_pathjoin', 'select_writable_path',
           'repo_version', 'git_version', 'hg_version', 'svn_version')


def _resolve_name(name, package, level):
    '''
    Return the absolute name of the module to be imported.

    (taken from django.utils.importlib)
    '''
    if not hasattr(package, 'rindex'):
        raise ValueError('\'package\' not set to a string')
    dot = len(package)
    for x in range(level, 1, -1):
        try:
            dot = package.rindex('.', 0, dot)
        except ValueError:
            raise ValueError('attempted relative import beyond top-level '
                             'package')
    return '%s.%s' % (package[:dot], name)


def import_module(name, package=None):
    '''
    Import a module. This is rather old and obsolete.

    The 'package' argument is required when performing a relative import. It
    specifies the package to use as the anchor point from which to resolve the
    relative import to an absolute import.

    (taken from django.utils.importlib)
    '''
    if name.startswith('.'):
        if not package:
            raise TypeError("relative imports require the 'package' argument")
        level = 0
        for character in name:
            if character != '.':
                break
            level += 1
        name = _resolve_name(name[level:], package, level)
    __import__(name)
    return modules[name]  # sys.modules


def ascii_filename(path, replacement='X'):
    '''
    Strip all low ascii and high ascii from path.

    >>> ascii_filename('ascii')
    'ascii'

    >>> ascii_filename('\\nab\\0c\\x81')
    'XabXcX'

    >>> ascii_filename(u'unicode')
    u'unicode'

    >>> ascii_filename(u'euro\\u20acsign\\xa0')
    u'euroXsignX'

    >>> ascii_filename(u'\\1-\\2\\3', replacement='abc')
    u'abc-abcabc'

    >>> try: x = ascii_filename(None)
    ... except TypeError: None
    ... else: print('Got: %r' % x)
    '''
    if isinstance(path, str):
        return ascii_filename.str_re.sub(replacement, path)
    if isinstance(path, unicode):
        return ascii_filename.uni_re.sub(replacement, path)
    raise TypeError('Expected basestring, got %s: %r' %
                    (path.__class__.__name__, path))
ascii_filename.str_re = re.compile(r'[\x00-\x1f\x80-\xff]')
ascii_filename.uni_re = re.compile(u'[\u0000-\u001f\u0080-\uffff]')


def assert_writable(paths, for_other_user=False):
    '''
    Check that a list of directories is writable. Do this at startup
    from the settings file, to ensure that you won't have a permission
    denied later on in your running app.

    Example at end of django settings file:
    assert_writable(_WRITABLE_PATHS, for_other_user=('www-data', False)[DEBUG])
    '''
    errors = []
    for path in paths:
        if for_other_user:
            # <for_other_user> should be able to write to it (check uid
            # or mode).
            expected_id = pwd.getpwnam('www-data').pw_uid
            try:
                st = os.stat(path)
            except OSError as e:
                errors.append('%s: %s' % (path, e))
            else:
                if not stat.S_ISDIR(st.st_mode):
                    errors.append('%s: Not a directory' % (path,))
                elif stat.S_IMODE(st.st_mode) & 0x7 == 0x7:  # rwx
                    pass
                elif st.st_uid == expected_id:
                    pass
                else:
                    errors.append(
                        '%s: Expected uid %d (%s), but st_uid = %d '
                        'with mode %o.' % (
                            path, expected_id, for_other_user,
                            st.st_uid, st.st_mode))
        else:
            # We should be able to write to it.
            try:
                os.makedirs(path)
            except OSError:
                pass  # file exists
            try:
                fd, filename = mkstemp(dir=path)
            except OSError as e:
                errors.append('%s: %s' % (path, e))
            else:
                os.close(fd)
                os.unlink(filename)
    if errors:
        raise AssertionError(
            'Not all file paths are writable by the app:\n  %s' % (
                 '\n  '.join(errors),))


def file_needs_updating(filename, write_every, do_not_write_after=None):
    '''
    Test if the file needs to be updated according to the modification time.
    If the file hasn't been updated for 'write_every' seconds or more, or
    the file does not exist or is empty, this function returns True.

    Supply a 'do_not_write_after' datetime to let it return False if the
    file exists and is non-empty but 'do_not_write_after' has passed.

    >>> import os, tempfile, time
    >>> from datetime import datetime, timedelta
    >>> # filesystem time has low granularity, so deduct a second or two here
    >>> now = datetime.now() - timedelta(seconds=2)
    >>> fd, filename = tempfile.mkstemp()
    >>> os.close(fd); os.unlink(filename)
    >>> (file_needs_updating(filename, 123) and
    ...  file_needs_updating(filename, 123, now))
    True
    >>> count = open(filename, 'w').write('abc')  # XXX use tmpnam?
    >>> st = os.stat(filename)
    >>> file_needs_updating(filename, 1)
    False
    >>> time.sleep(2)  # sleep more than 1 second..
    >>> file_needs_updating(filename, 1)  # ..now this returns true
    True
    >>> file_needs_updating(filename, 1, now)
    False
    >>> file_needs_updating(filename, 1, now + timedelta(seconds=60))
    True
    >>> os.unlink(filename)
    '''
    try:
        fileinfo = os.stat(filename)
    except os.error:
        return True

    tz = None
    if do_not_write_after:
        tz = do_not_write_after.tzinfo

    size, mtime = fileinfo[6], datetime.fromtimestamp(fileinfo[8], tz=tz)
    now = datetime.now(tz=tz)
    if size == 0:
        return True
    if mtime + timedelta(seconds=write_every) <= now:
        if do_not_write_after is None:
            return True
        if mtime <= do_not_write_after:
            return True
    return False


def safe_pathjoin(basepath, *concatpaths):
    '''
    Join basepath and concatpath, canonicalize it (remove ../) and assert that
    the result is still in basepath.

    If that fails, it tries to raise a django SuspiciousOperation, or if that
    cannot be imported, a ValueError.

    Observe that concatpaths starting with '/' are allowed, but will be treated
    as if it starts with './'.

    We take more than one argument.

    >>> try: safe_pathjoin()
    ... except TypeError: pass
    ... else: assert False

    One or more argument.

    >>> safe_pathjoin('/tmp')
    '/tmp'
    >>> safe_pathjoin('/', 'tmp')
    '/tmp'
    >>> safe_pathjoin('/', 'tmp', '2')
    '/tmp/2'

    We remove leading and trailing slashes.

    >>> safe_pathjoin('/tmp', '/tmp2')
    '/tmp/tmp2'
    >>> safe_pathjoin('/tmp/', '/tmp2/')
    '/tmp/tmp2'

    We canonicalize things.

    >>> safe_pathjoin('/tmp', 'tmp2', '..', 'tmp3')
    '/tmp/tmp3'
    >>> safe_pathjoin('/tmp', 'tmp2/..///tmp3')
    '/tmp/tmp3'

    On to the "safe" bit, ensure that we can NOT break out of the basepath.

    >>> try: safe_pathjoin('/tmp/3', '../tmp3')
    ... except: pass
    ... else: assert False
    >>> try: safe_pathjoin('/tmp/3', '..', 'tmp3')
    ... except: pass
    ... else: assert False

    But we are allowed to surf up and back.

    >>> safe_pathjoin('/tmp/3', '..', '.', '/3/.//4')
    '/tmp/3/4'
    '''
    # Preprocessing: check arguments and remove leading slashes
    assert basepath[0] == '/', ('Expected basepath with leading slash: %r' %
                                (basepath,))
    basepath = basepath.rstrip('/')
    if not basepath:
        basepath = '/'  # basepath ends with '/' only if it's the root
    concatpaths = [i.strip('/') for i in concatpaths]

    # Implement actual functionality: join and normalize (remove . and ..)
    joined = os.path.normpath(os.path.join(basepath, *concatpaths))
    # .. and remove trailing slashes.
    joined = joined.rstrip('/')

    # Do the suspicious operation check: what makes us safe.
    if joined.startswith(basepath + '/'):
        pass  # most common case
    elif joined == basepath:
        pass  # no args?
    elif basepath == '/' and joined.startswith('/'):
        pass  # basepath was '/'
    else:
        try:
            from django.core.exceptions import SuspiciousOperation
        except ImportError:
            SuspiciousOperation = ValueError
        raise SuspiciousOperation('Tried to break out of base path',
                                  basepath, concatpaths, joined)

    # Postprocessing: remove trailing slashes, check results
    assert joined[0] == '/', ('Expected output with leading slash: %r' %
                              (joined,))

    # Return the results
    return joined


def select_writable_path(paths):
    '''
    Returns the path from the list that is writable. An attempt to
    create the path is made if it doesn't exist.

    Absolute paths are treated as such, relative paths are considered
    to be relative to the first path found in the PYTHONPATH environment
    variable (or the current working directory if PYTHONPATH is empty).
    setting. The autolog.path setting can be a colon-delimited list of
    paths to try.

    Returns None if no path is found.

    >>> import os
    >>> is_root = (os.geteuid() == 0) # do nothing when root
    >>> old_PYTHONPATH = os.environ.get('PYTHONPATH')
    >>> os.environ['PYTHONPATH'] = '/tmp/testdir'
    >>> os.makedirs('/tmp/testdir', 0o700)
    >>> os.makedirs('/tmp/testdir/writable', 0o700)
    >>> os.makedirs('/tmp/testdir/nowrite', 0o500)

    >>> ((is_root and '/tmp/testdir/writable/b') or
    ...  select_writable_path(['/tmp/testdir/nowrite/a',
    ...                        '/tmp/testdir/writable/b',
    ...                        '/tmp/testdir/nowrite/c']))
    '/tmp/testdir/writable/b'
    >>> ((is_root and '/tmp/testdir/./writable/b') or
    ...  select_writable_path(['./nowrite/a', './writable/b', './nowrite/c']))
    '/tmp/testdir/./writable/b'
    >>> if not is_root:
    ...     select_writable_path(['./nowrite/a', './nowrite/c'])

    >>> if not is_root:
    ...     os.rmdir('/tmp/testdir/writable/b')
    >>> os.rmdir('/tmp/testdir/writable')
    >>> os.rmdir('/tmp/testdir/nowrite')
    >>> os.rmdir('/tmp/testdir')
    >>> if old_PYTHONPATH is None: del os.environ['PYTHONPATH']
    ... else: os.environ['PYTHONPATH'] = old_PYTHONPATH
    '''
    # Bah, PYTHONPATH[0] is probably not the best "default" location.
    # Should fix this and the tests above.
    # fallback_root = <here>/osso/core/fileutil.py
    fallback_root = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))

    for path in paths:
        path = path.strip()
        if len(path) == 0:
            continue

        if path[0] != os.path.sep:
            base_path = (os.environ.get('PYTHONPATH', fallback_root)
                         .split(os.pathsep, 1))[0]  # (pathsep=':'/';')
            path = os.path.join(base_path, path)

        if not os.access(path, os.F_OK | os.R_OK | os.W_OK | os.X_OK):
            try:
                os.makedirs(path, 0o700)
            except OSError:
                continue

        break  # found
    else:
        path = None

    return path


def repo_version(path):
    '''
    Loop over the possible versioning systems in an attempt to find
    a version number of some kind.

    Observe that svn_version returns a single number only, hg_version
    returns a hexadecimal revision and git_version returns a hexadecimal
    revision *plus* an optional 'm' for modified.
    '''
    # The version functions return 0 if unknown, so the following works.
    for version_func in (git_version, hg_version, svn_version):
        num = version_func(path)
        if num != '0':
            break
    return num


def git_version(path):
    '''
    Determine the git revision id of the specific path or file. (Add 'm'
    for dirty version.

    >>> all(i in '0123456789abcdefm' for i in git_version('.'))
    True
    >>> git_version('.') >= '0'
    True
    '''
    # Git has only one root, we have to call it with the right CWD.
    try:
        error = None
        # We could add ( git status -suno | grep -q '' && echo -n m )
        # here to get the dirtyness, but we need git-owner powers to
        # be able to lock the repo for that.
        proc = Popen(('git', 'log', '-1', '--format=format:%h'), cwd=path,
                     stdout=PIPE, stderr=PIPE)
        data = proc.communicate()
        if proc.wait() != 0:  # finish running the process and get status
            error = 'command: git log -1 --format=format:%h, returned non-zero'
    except OSError as e:
        error = ('command: git log -1 --format=format:%%h, error: %s' %
                 (e.args[0],))

    if not error:
        data = (data[0].decode('utf-8', 'replace'),
                data[1].decode('utf-8', 'replace'))
        try:
            # Output may be followed by a plus and a linefeed
            # (no 'm' if we're not doing 'git describe' which was wrong
            # anyway)
            num = ''.join(i for i in data[0] if i in '0123456789abcdefm')
        except (AssertionError, ValueError):
            error = ('command: git log -1 --format=format:%%h, stdout: %s, '
                     'stderr: %s' % (data[0], data[1]))

    if error:
        num = '0'
    return num


def hg_version(path):
    '''
    Determine the mercurial revision id of the specific path or file.
    (We cannot use -n, so version numbers will now be allowed to be in
    hex.)

    >>> all(i in '0123456789abcdef' for i in hg_version('.'))
    True
    >>> hg_version('.') >= '0'
    True
    '''
    # Mercurial has only one root, we have to call it with the right
    # CWD.
    try:
        error = None
        proc = Popen(('hg', 'id', '-i'), cwd=path, stdout=PIPE, stderr=PIPE)
        data = proc.communicate()
        if proc.wait() != 0:  # finish running the process and get status
            error = 'command: hg id -i, returned non-zero'
    except OSError as e:
        error = 'command: hg id -i, error: %s' % (e.args[0],)

    if not error:
        data = (data[0].decode('utf-8', 'replace'),
                data[1].decode('utf-8', 'replace'))
        try:
            # output may be followed by a plus and a linefeed
            num = ''.join(i for i in data[0] if i in '0123456789abcdef')
        except (AssertionError, ValueError):
            error = ('command: hg id -i, stdout: %s, stderr: %s' %
                     (data[0], data[1]))

    if error:
        num = '0'
    return num


def svn_version(path):
    '''
    Determine the subversion revision number of the specified path or
    file. If the path (or file) is not versioned, the svn binary cannot
    be found or some other error occurs, '0' is returned.

    Observe that for compatibility with hg_version a string is returned.

    >>> svn_version('.').isdigit()
    True
    >>> svn_version('.') >= '0'
    True
    '''
    try:
        proc = Popen(('svn', 'info', path), stdout=PIPE, stderr=PIPE)
        output = proc.communicate()[0].decode('utf-8', 'replace')
        if proc.wait() != 0:  # finish running the process and get status
            return '0'
    except OSError:
        return '0'

    num = 0
    for line in output.split('\n'):
        if line.startswith('Revision: '):
            try:
                num = int(line[10:].strip())
            except ValueError:
                pass
            else:
                break
    return str(num)
