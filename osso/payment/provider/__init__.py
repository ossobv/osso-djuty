# vim: set ts=8 sw=4 sts=4 et ai:
from django.conf import settings
from django.utils.importlib import import_module


def clean_description(description):
    # XXX: this won't work in the long run: we already want both an
    # ideal provider and a paypal provider.
    provider_module = import_module(settings.OSSO_PAYMENT['provider'])
    return provider_module.clean_description(description)

def get_ideal_instance():
    # XXX: this won't work in the long run: we already want both an
    # ideal provider and a paypal provider.
    ideal_module = import_module(settings.OSSO_PAYMENT['provider'] + '.ideal')
    return ideal_module.Ideal(testing=settings.OSSO_PAYMENT.get('test_mode', False))

def get_msp_instance():
    # XXX: see above :)
    msp_module = import_module('osso.payment.provider.msp.msp')
    return msp_module.MultiSafepay(testing=settings.OSSO_PAYMENT.get('test_mode', False))

def get_paypal_instance():
    # XXX: see above :)
    paypal_module = import_module('osso.payment.provider.paypal.paypal')
    return paypal_module.Paypal(testing=settings.OSSO_PAYMENT.get('test_mode', False))
