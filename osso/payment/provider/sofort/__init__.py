# vim: set ts=8 sw=4 sts=4 et ai:
import unicodedata


def clean_description(description):
    # 27 characters is the Sofort limit for the description.
    # It only likes the characters listed here.
    description = unicodedata.normalize('NFKD', description).encode('ascii', 'ignore')
    description = ''.join(i for i in description if i in '0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz +,-.')
    if len(description) > 27:
        description = description[0:24] + '...'
    return description
