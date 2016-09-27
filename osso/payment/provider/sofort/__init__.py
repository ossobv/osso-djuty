# vim: set ts=8 sw=4 sts=4 et ai:
"""
API: https://www.sofort.com/integrationCenter-eng-DE/content/view/full/2865
"""
import unicodedata

from osso.payment import use_test_mode

from .sofort import Sofort


# Only the following characters are allowed in the parameters reason_1
# and reason_2: '0-9', 'a-z', 'A-Z', ' ', '+', ',', '-', '.'. Umlauts
# are replaced, e.g. ä -> ae. Other characters will be removed for the
# display on our payment page and for notifications.
# (Almost all variables are capped at 27 chars.)
VALID_DESCRIPTION_TOKENS = (
    '0123456789'
    'ABCDEFGHIJKLMNOPQRSTUVWXYZ'
    'abcdefghijklmnopqrstuvwxyz'
    ' +,-.')
VALID_DESCRIPTION_LENGTH = 27


def clean_description(description):
    description = unicodedata.normalize('NFKD', description).encode(
        'ascii', 'ignore')
    description = ''.join(
        i for i in description if i in VALID_DESCRIPTION_TOKENS)
    if len(description) > VALID_DESCRIPTION_LENGTH:
        description = description[0:(VALID_DESCRIPTION_LENGTH - 3)] + '...'
    return description


def get_instance():
    return Sofort(testing=use_test_mode())
