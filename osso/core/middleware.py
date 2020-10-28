# vim: set ts=8 sw=4 sts=4 et ai:
import logging
from os import uname
from resource import getrusage
from time import time

from django.core.exceptions import MiddlewareNotUsed


__all__ = ('LogRequestsMiddleware',
           'RusageMiddleware')


logger = logging.getLogger(__name__)


class LogRequestsMiddleware(object):
    '''
    Log the beginning and end time of every request to a log file. This
    is a crude way to see which pages need optimization.
    '''
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        t0 = time()
        meta = request.META
        logger.debug(
            '%-15s %s %s?%s', meta['REMOTE_ADDR'], request.method,
            meta['PATH_INFO'], meta['QUERY_STRING'])

        response = self.get_response(request)

        spent = time() - t0
        logger.debug(
            '%-15s %s %s?%s (%.4f seconds)', meta['REMOTE_ADDR'],
            request.method, meta['PATH_INFO'], meta['QUERY_STRING'], spent)

        return response


class RusageMiddleware(object):
    """
    FIXME: this needs documentation
    """
    # Works in Linux 2.6, exists first in Python 3.2
    RUSAGE_THREAD = 1

    def __init__(self, get_response):
        self.get_response = get_response

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

    def __call__(self, request):
        t0 = time()
        rusage0 = getrusage(self.RUSAGE_THREAD)

        response = self.get_response(request)

        rtime = time() - t0
        rusage = getrusage(self.RUSAGE_THREAD)
        utime = rusage.ru_utime - rusage0.ru_utime
        stime = rusage.ru_stime - rusage0.ru_stime

        # TODO: only log past a threshold?
        logger.debug(
            'method=%(method)s path=%(path)s ct=%(content_type)s '
            'rtime=%(rtime).3f utime=%(utime).3f stime=%(stime).3f '
            'qs=%(query_string)s', {
                'method': request.method,
                'path': request.get_full_path(),
                'content_type': response['content-type'].split(';', 1)[0],
                'rtime': rtime,
                'utime': utime,
                'stime': stime,
                'query_string': request.META['QUERY_STRING']})

        return response
