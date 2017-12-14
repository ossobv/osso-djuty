# vim: set ts=8 sw=4 sts=4 et ai:
import logging

from django.conf import settings


__all__ = ('IgnoreUploadError', 'get_open_fds')


class IgnoreUploadError(logging.Filter):
    """
    Ignore errors during upload. We especially don't want e-mail of
    these.

    This should've been fixed by
    osso.core.middleware.IgnoreUploadErrorMiddleware, but usually the
    error occurs during the csrfmiddleware reading request.POST:

        django/middleware/csrf.py", line 172, in process_view
            request_csrf_token = request.POST.get('csrfmiddlewaretoken', '')
        ...
        IOError: error reading for wsgi.input data: Content-Length \\
                1709950 requested 65536 received 45056 pos 65536+45056

    Example usage:

        > @@ -148,6 +148,9 @@
        >      'version': 1,
        >      'disable_existing_loggers': False,
        >      'filters': {
        > +        'ignore_upload_error': {
        > +            '()': 'osso.core.logutil.IgnoreUploadError',
        > +        },
        >          'require_debug_false': {
        >              #'()': 'django.utils.log.RequireDebugFalse' # django1.4+
        >              '()': RequireDebugFalse, # for django1.3 and older
        > @@ -156,7 +159,8 @@
        >      'handlers': {
        >          'mail_admins': {
        >              'level': 'ERROR',
        > -            'filters': ['require_debug_false'],
        > +            'filters': ['require_debug_false',
        > +                        'ignore_upload_error'],
        >              'class': 'django.utils.log.AdminEmailHandler'
        >          },
        >      },
    """
    error_substrings = (
        # mod_wsgi (apache)
        'request data read error',
        # uwsgi, 1.0.old:
        'error reading wsgi.input data',
        # uwsgi, 1.4.9:
        'error reading for wsgi.input data',
    )

    def filter(self, record):
        if record.exc_info:
            class_, exception, tb = record.exc_info
            if (class_ == IOError and
                    exception.args and
                    isinstance(exception.args[0], basestring)):
                for substring in self.error_substrings:
                    if exception.args[0].find(substring) != -1:
                        # Don't report this error.
                        return False
        # Do report this error.
        return True


def get_open_fds():
    """
    When daemonizing, all FDs get closed after the fork(). This breaks logging.

    Pass the result of this function to the DaemonContext files_preserve
    parameter (a list of fds).
    """
    # SUPERYUCK! We don't know which loggers we'll need.. fetching all loggers
    # that we have registered.
    handlers = set()
    for logkey in settings.LOGGING['loggers'].keys():
        logger = logging.getLogger(logkey)
        handlers |= set(logger.handlers)

    log_fds = []
    # FileHandlers
    log_fds.extend(i.stream.fileno() for i in handlers if hasattr(i, 'stream'))
    # SyslogHandlers
    log_fds.extend(i.socket.fileno() for i in handlers if hasattr(i, 'socket'))

    return log_fds
