# vim: set ts=8 sw=4 sts=4 et ai:
"""
API: not found on the net anymore...
"""
import unicodedata

from osso.payment import use_test_mode


# 29 characters is the Mollie limit for the description.
# And we're pretty sure it doesn't like certain characters.
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
    from .ideal import Ideal
    return Ideal(testing=use_test_mode())
