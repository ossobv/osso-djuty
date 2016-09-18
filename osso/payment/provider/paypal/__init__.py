# vim: set ts=8 sw=4 sts=4 et ai:
"""
API: https://developer.paypal.com/docs/classic/api/merchant/SetExpressCheckout_API_Operation_NVP/
"""
import unicodedata

from osso.payment import use_test_mode


# Character length and limitations: 127 single-byte alphanumeric characters.
VALID_DESCRIPTION_TOKENS = (
    '0123456789'
    'ABCDEFGHIJKLMNOPQRSTUVWXYZ'
    'abcdefghijklmnopqrstuvwxyz'
    ' +,-.')
VALID_DESCRIPTION_LENGTH = 127


def clean_description(description):
    description = unicodedata.normalize('NFKD', description).encode(
        'ascii', 'ignore')
    description = ''.join(
        i for i in description if i in VALID_DESCRIPTION_TOKENS)
    if len(description) > VALID_DESCRIPTION_LENGTH:
        description = description[0:(VALID_DESCRIPTION_LENGTH - 3)] + '...'
    return description


def get_instance():
    from .paypal import Paypal
    return Paypal(testing=use_test_mode())
