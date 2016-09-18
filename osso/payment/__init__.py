# vim: set ts=8 sw=4 sts=4 et ai:
from django.conf import settings


class BuyerError(ValueError):
    pass

class PaymentAlreadyUsed(BuyerError):
    '''This payment has been used already. User has gone back to a
    payment page where he should not be.'''
    pass

class PaymentSuspect(BuyerError):
    '''Something looks fishy.'''
    pass

class TryDifferentPayment(BuyerError):
    '''Provider says you have no money or chose the wrong payment
    method.'''
    pass


class ProviderError(IOError):
    pass

class ProviderBadConfig(ProviderError):
    '''Configuration error, probably bad API key and/or credentials.'''
    pass

class ProviderDown(ProviderError):
    '''Provider or upstream bank is down (likely individual iDEAL banks
    being down).'''

    def __init__(self, provider, bank=None):
        if bank:
            message = '%s (through %s) is down' % (bank, provider)
        else:
            message = '%s is down' % (provider,)

        super(ProviderDown, self).__init__(message)


def use_test_mode():
    """
    Returns True if OSSO_PAYMENT is in test_mode.
    """
    return settings.OSSO_PAYMENT.get('test_mode', False)
