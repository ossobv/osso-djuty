# vim: set ts=8 sw=4 sts=4 et ai:
"""
API: https://www.multisafepay.com/documentation/doc/API-Reference/
"""
import unicodedata

from osso.payment import use_test_mode

from .msp import MultiSafepay


# This is not defined. But 29 chars appears to be a safe bet.
VALID_DESCRIPTION_TOKENS = (
    '0123456789'
    'ABCDEFGHIJKLMNOPQRSTUVWXYZ'
    'abcdefghijklmnopqrstuvwxyz'
    ' +,-.')
VALID_DESCRIPTION_LENGTH = 29


def clean_description(description):
    description = unicodedata.normalize('NFKD', description).encode(
        'ascii', 'ignore')
    description = ''.join(
        i for i in description if i in VALID_DESCRIPTION_TOKENS)
    if len(description) > VALID_DESCRIPTION_LENGTH:
        description = description[0:(VALID_DESCRIPTION_LENGTH - 3)] + '...'
    return description


def get_instance():
    return MultiSafepay(testing=use_test_mode())
