# vim: set ts=8 sw=4 sts=4 et ai:
from django.conf import settings
from django.core.exceptions import ImproperlyConfigured
try:
    from django.utils.importlib import import_module
except ImportError:
    from osso.core.fileutil import import_module


__all__ = ('BackendError', 'DestinationError', 'TransientError',
           'get_connection', 'BaseSmsBackend')


class BackendError(Exception):
    pass


class DestinationError(BackendError):
    pass


class TransientError(Exception):
    pass


def get_connection(backend=None, fail_silently=False, **kwargs):
    '''
    >>> from django.conf import settings
    >>> from osso.sms import get_connection
    >>> from osso.sms.models import TextMessage
    >>> connection = get_connection(
    ...     'osso.sms.backends.sms_console.ConsoleSmsBackend')
    >>> t = TextMessage.objects.create(
    ...     status='out', local_address='TEST',
    ...     remote_address='+31502103520', connection=connection,
    ...     body='I think I broke it !')
    >>> t.send()  # doctest: +ELLIPSIS
    TextMessage(id=1): Outbound SMS to +31502103520 at ...
    I think I broke it !
    -------------------------------------------------------------------------------
    1
    '''
    path = backend or getattr(settings, 'SMS_BACKEND', None)
    if path is None:
        raise ImproperlyConfigured('You need to specify a SMS_BACKEND '
                                   'in your settings')

    try:
        mod_name, klass_name = path.rsplit('.', 1)
        mod = import_module(mod_name)
    except ImportError as e:
        raise ImproperlyConfigured('Error importing sms backend module '
                                   '%s: "%s"' % (mod_name, e))

    try:
        klass = getattr(mod, klass_name)
    except AttributeError:
        raise ImproperlyConfigured('Module "%s" does not define a '
                                   '"%s" class' % (mod_name, klass_name))

    return klass(fail_silently=fail_silently, **kwargs)


class BaseSmsBackend(object):
    '''
    Base class for sms backend implementations.

    Subclasses must at least overwrite send_messages().
    '''
    def __init__(self, fail_silently=False, **kwargs):
        self.fail_silently = fail_silently

    def send_messages(self, sms_messages, reply_to=None,
                      shortcode_keyword=None, tariff_cent=None):
        '''
        Send one or more TextMessage objects and return the number of
        sent messages.
        '''
        raise NotImplementedError()
