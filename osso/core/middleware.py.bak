# vim: set ts=8 sw=4 sts=4 et ai:
import logging
from os import uname
from resource import getrusage
from sys import exc_info
from time import time

from django import VERSION
from django.conf import settings
from django.contrib.auth import views as auth_views
from django.core.exceptions import MiddlewareNotUsed
from django.core.urlresolvers import reverse
from django.db import connection
from django.http import HttpResponse, HttpResponseRedirect
from osso.core.decorators import log_failed_logins
try:
    from osso.autolog.utils import log
except ImportError:
    pass  # we only need it for LogRequestsMiddleware


__all__ = ('LogFailedLoginsMiddleware',
           'LogRequestsMiddleware',
           'LogSqlToConsoleMiddleware',
           'NoDisabledUsersMiddleware',
           'IgnoreUploadErrorMiddleware',
           'RusageMiddleware')


logger = logging.getLogger(__name__)


class LogFailedLoginsMiddleware(object):
    '''
    Write a line to stderr for every failed django login. Web servers
    like apache write these in the error log.

    Use fail2ban or something similar to block brute-force attacks. (See
    fail2ban.diff in this directory.)

    This middleware may *break* builtin Django auth tests:

    > File "/opt/django13/django/contrib/auth/tests/views.py",
    >   line 211, in test_security_check
    > ...
    > NoReverseMatch: Reverse for 'django.contrib.auth.views.login'
    >   with arguments '()' and keyword arguments '{}' not found.

    That occurs if a middleware has called reverse() already and
    therefore cached the value of the original login view -- which is
    later used for the reverse lookup.

    Fix 1: the hacks below (``i._callback = auth_views.login``).
    Fix 2: move this middleware up a bit, so no reverse() has been
           called yet.
    '''
    def __init__(self, *args, **kwargs):
        super(LogFailedLoginsMiddleware, self).__init__(*args, **kwargs)

        # If all is well, this constructor is called exactly once.
        # Unfortunately some python-http interfaces (mod_python) call
        # this constructor more than once: we work around this by
        # checking whether we already wrapped it. Note that this fails
        # if multiple decorators are attached to the login function.
        if not hasattr(auth_views.login, '__is_decorator'):
            # Wrap the regular auth login
            original = auth_views.login
            auth_views.login = log_failed_logins(auth_views.login)

            # Fix test failures that arise if someone has already
            # called reverse() before this middleware is loaded.
            # If they did, the urlpattern would be cached and the
            # reverse lookup would contain the old view instead
            # of the new.
            # Tested against Django 1.4.19 on 2015-08-13.
            try:
                # from django.core.urlresolvers import clear_url_caches
                # clear_url_caches()
                from django.contrib.auth import urls
                for i in urls.urlpatterns:
                    if i.callback == original:
                        i._callback = auth_views.login
            except:
                pass

        # Same goes for the admin-site login. Note that since Django
        # 1.3 this uses the auth login function. We only do this for
        # old versions.
        if VERSION < (1, 3):
            from django.contrib import admin
            if not hasattr(admin.site.login, '__is_decorator'):
                # Wrap the /admin/ login
                admin.site.login = log_failed_logins(admin.site.login)


class LogRequestsMiddleware(object):
    '''
    Log the beginning and end time of every request to a log file. This
    is a crude way to see which pages need optimization.
    '''
    def process_request(self, request):
        request.t0 = time()
        meta = request.META
        msg = ('%-15s %s %s?%s' %
               (meta['REMOTE_ADDR'], request.method, meta['PATH_INFO'],
                meta['QUERY_STRING']))
        log(msg, log='request', subsys='begin')
        return None

    def process_response(self, request, response):
        spent = time() - request.t0
        meta = request.META
        msg = ('%-15s %s %s?%s (%.4f seconds)' %
               (meta['REMOTE_ADDR'], request.method, meta['PATH_INFO'],
                meta['QUERY_STRING'], spent))
        log(msg, log='request', subsys='end  ')
        return response


class LogSqlToConsoleMiddleware(object):
    '''
    Log all SQL statements direct to the console (in debug mode only).
    Intended for use with the django development server.

    Insert as first element in MIDDLEWARE_CLASSES when you need it.

    http://www.djangosnippets.org/snippets/1672/ by davepeck, 6-aug-2009.
    '''
    def process_request(self, request):
        self.t0 = time()
        return None

    def process_response(self, request, response):
        if (settings.DEBUG and
                connection.queries and
                (not settings.MEDIA_URL or
                 not (request.META['PATH_INFO']
                      .startswith(settings.MEDIA_URL))) and
                not request.META['PATH_INFO'].startswith('/jsi18n/')):
            print('\n' + '=' * 72)

            if 'time' in connection.queries[0]:
                total = sum(float(q['time']) for q in connection.queries)
                for i, query in enumerate(connection.queries):
                    print('>>> (%d) %ss: %s' %
                          (i, query['time'], query['sql']))
                print('== %d queries in %f seconds ==\n' %
                      (len(connection.queries), total))

            else:
                for i, query in enumerate(connection.queries):
                    print('>>> (%d): %s' % (i, query['sql']))
                print('== %d queries in %f seconds ==' %
                      (len(connection.queries), time() - self.t0))

        return response


class NoDisabledUsersMiddleware(object):
    '''
    Logs out users that are set to is_active=False automatically. When
    you switch the user state, the user still keeps his session. Force
    the user to the logout page.

    This must be loaded after the session middleware.

    NOTE: if you're trying to tone down the queries, this one does an
    auth_user query. See osso.core.sessutil.ueber_logout for a
    different solution where you purge the session cache at user-
    deactivation time.

    You should probably invoke that whenever you change a password too.
    '''
    def process_request(self, request):
        user = request.user
        if user.is_authenticated() and not user.is_active:
            logout_url = reverse('logout')
            if request.path != logout_url:
                return HttpResponseRedirect(logout_url)


class IgnoreUploadErrorMiddleware(object):
    """A stab at ignoring user-upload errors.

    See also for a different solution:
    http://stackoverflow.com/questions/2375950/getting-rid-of-django-ioerrors
    http://stackoverflow.com/questions/3823280/ioerror-request-data-read-error
    https://github.com/django/django/commit/0ce6636102

    As a special addition, we do not only catch the errors and ignore
    them, if they are triggered. We also attempt to trigger them
    directly.

    Why? Because exceptions in middleware are not passed to the
    exception handler (in Django 1.4): this means that the
    CSRF-middleware will almost always catch the error (and raise it)
    and we won't get to ignore it.
    """
    exceptions = (
        IOError,
    )
    errorsubstrings = (
        # mod_wsgi (apache)
        'request data read error',
        # uwsgi, 1.0.old:
        'error reading wsgi.input data',
        # uwsgi, 1.4.9:
        #   plugins/python/wsgi_handlers.c:
        #     return PyErr_Format(PyExc_IOError,
        #       "error reading for wsgi.input data: Content-Length %llu "
        #       "requested %llu received %llu pos %llu+%llu",
        #       (unsigned long long) self->wsgi_req->post_cl, ...);
        'error reading for wsgi.input data',
        # uwsgi, 1.9.17: IOError: error during read(65536) on wsgi.input
        'error during read(',
    )
    functions = (
        '_load_post_and_files',
    )

    def process_request(self, request, *args, **kwargs):
        if request.method == 'POST':
            try:
                # Trigger the self._load_post_and_files call which
                # eventually results in the IOError.
                request.POST.get('csrfmiddlewaretoken')
            except Exception, e:
                response = self.process_exception(request, e)
                if response:
                    return response
                # Re-raise the exception.
                raise

    def process_exception(self, request, exception):
        if (isinstance(exception, self.exceptions) and
                exception.args and
                isinstance(exception.args[0], basestring) and
                any(exception.args[0].find(i) != -1
                    for i in self.errorsubstrings)):
            # Check the traceback for the right route too.
            _, _, tb = exc_info()
            while tb:
                if tb.tb_frame.f_code.co_name in self.functions:
                    # Ok. We have a match.
                    response = HttpResponse('', content_type='text/plain')
                    # nginx uses 499 as "client closed the connection"
                    response.status_code = 499
                    return response
                tb = tb.tb_next
        return None


class RusageMiddleware(object):
    """
    FIXME: this needs documentation
    """
    # Works in Linux 2.6, exists first in Python 3.2
    RUSAGE_THREAD = 1

    def __init__(self, *args, **kwargs):
        super(RusageMiddleware, self).__init__(*args, **kwargs)

        # Version check
        (sysname, nodename, release, version, machine) = uname()
        if (sysname == 'Linux' and
            [i.isdigit() and int(i) or 0
             for i in release.split('.')] >= [2, 6]):
            # Linux 2.6 or higher
            pass
        else:
            # Something else
            raise MiddlewareNotUsed('No RUSAGE_THREAD on %s %s' %
                                    (sysname, release))

    def process_request(self, request, *args, **kwargs):
        request._t0 = time()
        request._rusage = getrusage(self.RUSAGE_THREAD)

    def process_response(self, request, response):
        rtime = time() - request._t0
        rusage = getrusage(self.RUSAGE_THREAD)
        utime = rusage.ru_utime - request._rusage.ru_utime
        stime = rusage.ru_stime - request._rusage.ru_stime

        # TODO: only log past a threshold?
        msg = ('method=%(method)s path=%(path)s ct=%(content_type)s '
               'rtime=%(rtime).3f utime=%(utime).3f stime=%(stime).3f '
               'qs=%(query_string)s' %
               {'method': request.method,
                'path': request.get_full_path(),
                'content_type': response['content-type'].split(';', 1)[0],
                'rtime': rtime,
                'utime': utime,
                'stime': stime,
                'query_string': request.META['QUERY_STRING']})

        logger.info(msg)

        return response
