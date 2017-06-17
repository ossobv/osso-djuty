# vim: set ts=8 sw=4 sts=4 et ai:
"""
API: https://www.targetpay.com/info/bankwire-docu
API: https://www.targetpay.com/info/cc-docu
API: https://www.targetpay.com/info/ideal-docu
API: https://www.targetpay.com/info/mrcash-docu
"""
import unicodedata

from osso.payment import use_test_mode

from .targetpay import TargetpayCreditcard, TargetpayIdeal, TargetpayMrCash


# A clear description of the service. Maximum 32 characters. Only
# letters, numbers and the following characters: , . - _ * [] () and
# space.
#
# For both Creditcard and MrCash it says "[alleen] letters of cijfers,
# maximaal 32 tekens [...]" but I don't believe it would be only
# [A-Za-z0-9].
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


def get_instance(provider_sub=None):
    if provider_sub == 'creditcard':
        instance = TargetpayCreditcard(testing=use_test_mode())
    elif provider_sub == 'ideal':
        instance = TargetpayIdeal(testing=use_test_mode())
    elif provider_sub == 'mrcash':
        instance = TargetpayMrCash(testing=use_test_mode())
    else:
        raise NotImplementedError(
            'implemented creditcard/ideal/mrcash, not {}'.format(provider_sub))

    return instance
