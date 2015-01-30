# vim: set ts=8 sw=4 sts=4 et ai:
import unicodedata


def clean_description(description):
    # 29 characters is the Mollie limit for the description.
    # And we're pretty sure it doesn't like certain characters.
    description = unicodedata.normalize('NFKD', description).encode('ascii', 'ignore')
    description = ''.join(i for i in description if i in '0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz +,-.')
    if len(description) > 29:
        description = description[0:26] + '...'
    return description
