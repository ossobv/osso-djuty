# vim: set ts=8 sw=4 sts=4 et ai:
"""
API: https://www.targetpay.com/info/ideal-docu
"""
import unicodedata

from osso.payment import use_test_mode


# A clear description of the service. Maximum 32 characters. Only
# letters, numbers and the following characters: , . - _ * [] () and
# space.
VALID_DESCRIPTION_TOKENS = (
    '0123456789'
    'ABCDEFGHIJKLMNOPQRSTUVWXYZ'
    'abcdefghijklmnopqrstuvwxyz'
    ' ,.-_*[]()')
VALID_DESCRIPTION_LENGTH = 32


def clean_description(description):
    description = unicodedata.normalize('NFKD', description).encode(
        'ascii', 'ignore')
    description = ''.join(
        i for i in description if i in VALID_DESCRIPTION_TOKENS)
    if len(description) > VALID_DESCRIPTION_LENGTH:
        description = description[0:(VALID_DESCRIPTION_LENGTH - 3)] + '...'
    return description


def get_instance():
    from .targetpay import TargetpayIdeal
    return TargetpayIdeal(testing=use_test_mode())
