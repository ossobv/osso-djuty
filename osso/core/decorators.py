# vim: set ts=8 sw=4 sts=4 et ai:
import re
import sys
import syslog
from django.contrib.auth.decorators import user_passes_test
from django.core.exceptions import ObjectDoesNotExist, PermissionDenied
try:
    from django.utils.decorators import available_attrs
except ImportError:
    available_attrs = None


__all__ = ('expect_get', 'expect_post',
           'login_with_profile_required',
           'log_failed_login')


# We strip the space so that our fail2ban regex cannot be tricked.
ILLEGAL_RE = re.compile('[\x00-\x1f\x80-\xff (),]+')  # no cntrl/space/(),/high


def expect_get(func):
    '''
    Allow only GET requests to come in, throw an exception otherwise.

    This relieves from checking every time that the request is
    really a GET request, which it should be when using this
    decorator.

    (stolen from dojango and fixed)
    '''
    def _ret(*args, **kwargs):
        if not args[0].method == 'GET':
            raise PermissionDenied('GET request expected.')
        return func(*args, **kwargs)
    return _ret


def expect_post(func):
    '''
    Allow only POST requests to come in, throw an exception otherwise.

    This relieves from checking every time that the request is
    really a POST request, which it should be when using this
    decorator.

    (stolen from dojango and fixed)
    '''
    def _ret(*args, **kwargs):
        if not args[0].method == 'POST':
            raise PermissionDenied('POST request expected.')
        return func(*args, **kwargs)
    return _ret


def login_with_profile_required(func):
    '''
    Decorator for views that checks that the user is logged in and
    checks that the user has a valid profile.
    '''
    def test(user):
        try:
            return user.is_authenticated and user.authenticatablecontact
        except ObjectDoesNotExist:
            # XXX: we should replace assert with something better
            assert False, 'User %s has no profile!' % user

    return user_passes_test(test)(func)


def log_failed_login(request, credentials=None, username=None, **kwargs):
    '''
    This is not a decorator, but can be used with the user_login_failed signal
    to log failed attempts.
    '''
    if username is None:
        if credentials is not None:
            username = credentials.get(
                'username', credentials.get('email', '/unset/'))
        else:
            username = request.POST.get('username', '/unset/')
    # For apache2 with mod-wsgi, we get this in the global
    # (non-site-specific) error.log:
    # [Sun Feb 27 16:12:29 2011] [error] THE_MESSAGE
    # The ILLEGAL_RE makes sure no improper characters get mixed in into
    # the message which would make it harder to parse.
    xff = ILLEGAL_RE.sub('', request.META.get('HTTP_X_FORWARDED_FOR', ''))
    if xff:
        xff = ', X-Forwarded-For: %s' % (xff,)
    msg = (
        '[django] Failed login for %(username)s '
        'from %(address)s port %(port)s (Host: %(host)s%(xff)s)\n'
    ) % {
        'username': ILLEGAL_RE.sub('?', username) or '/unset/',
        'address': request.META.get('REMOTE_ADDR', '/unset/'),
        'port': request.META.get('REMOTE_PORT', '/unset/'),
        'host': ILLEGAL_RE.sub('?', request.META.get('HTTP_HOST', '/unset/')),
        'xff': xff,
    }

    # Always use syslog. You should be checking auth.log
    # anyway for failed ssh logins. fail2ban has issues
    # with the uwsgi log which does not set timestamps on
    # every message.
    syslog.openlog(logoption=(syslog.LOG_PID | syslog.LOG_NDELAY),
                   facility=syslog.LOG_AUTH)
    syslog.syslog(syslog.LOG_WARNING, msg.encode('utf-8')[0:-1])  # strip LF

    # These log messages are here for further debugging and
    # backwards compatibility.
    if request.META.get('SERVER_SOFTWARE') == 'mod_python':
        from mod_python import apache
        apache.log_error(msg.encode('utf-8')[0:-1])  # strip LF
    elif sys.argv[1:2] != ['test']:  # no output during test runs
        # We could check for 'uwsgi.version' in request.META
        # and add strftime('%c'), but that log confuses
        # fail2ban so we won't bother.
        sys.stderr.write(msg.encode('utf-8'))
        sys.stderr.flush()  # mod_python needs this, others might too
