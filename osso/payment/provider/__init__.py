# vim: set ts=8 sw=4 sts=4 et ai:
from django.conf import settings
from django.utils.importlib import import_module
from osso.payment import use_test_mode


def get_provider_by_id(name):
    """
    Get the provider module. The provider module may have various
    methods, such as ``clean_description``.

    Example::

        provider = get_provider_by_id('msp')
        provider.clean_description("blah blah blah")

        instance = provider.get_instance()
    """
    module = import_module('osso.payment.provider.%s' % (name,))
    return module


# == OLD STUFF ==

def clean_description(description):
    """
    DEPRECATED! Don't use OSSO_PAYMENT['provider'] because we often
    have multiple providers.
    """
    provider_module = import_module(settings.OSSO_PAYMENT['provider'])
    return provider_module.clean_description(description)


def get_ideal_instance():
    """
    DEPRECATED! Don't use OSSO_PAYMENT['provider'] because we often
    have multiple providers.
    """
    ideal_module = import_module(settings.OSSO_PAYMENT['provider'] + '.ideal')
    return ideal_module.Ideal(testing=use_test_mode())


def get_mollie_ideal_instance():
    return get_provider_by_id('mollie').get_instance()


def get_msp_instance():
    return get_provider_by_id('msp').get_instance()


def get_sofort_ideal_instance():
    return get_provider_by_id('sofort').get_instance()


def get_paypal_instance():
    return get_provider_by_id('paypal').get_instance()
