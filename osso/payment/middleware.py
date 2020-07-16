# vim: set ts=8 sw=4 sts=4 et ai:
import sys

from django.shortcuts import render_to_response
from django.template import RequestContext
from django.utils.log import getLogger
try:
    from django.utils.deprecation import MiddlewareMixin
except ImportError:
    MiddlewareMixin = object

from osso.payment import ProviderDown

logger = getLogger('django.request')


class ProviderErrorMiddleware(MiddlewareMixin):
    """
    Right now, we only trap the ProviderDown exception that is thrown
    when there is a transient error with the payment provider. We catch
    the error and feed it to the 500-providerdown.html (or 500.html)
    template.

    This is used to catch a the-bank-is-down error from the Mollie
    iDEAL backend.
    """
    def process_exception(self, request, exception):
        if isinstance(exception, ProviderDown):
            # Make sure the error mail is sent, like normally.
            logger.error(
                'Internal Server Error: %s' % request.path,
                exc_info=sys.exc_info(),
                extra={
                    'status_code': 500,
                    'request': request,
                })
            # Show a different 500 page.
            context = {'error': exception}
            response = render_to_response(
                ('500-providerdown.html', '500.html'),
                context, context_instance=RequestContext(request))
            response.status_code = 500
            return response
        return None
