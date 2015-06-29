# vim: set ts=8 sw=4 sts=4 et ai:
import datetime
import decimal

from django import template
from django.utils.formats import get_format


register = template.Library()


@register.filter(name='hourstohuman')
def hourstohuman(value):
    '''
    Returns the decimal/float value as HH:MM(:SS).
    '''
    value = decimal.Decimal(str(value))
    hours, minutes, seconds = 0, 0, 0
    hours = int(value)
    value = (value % 1) * 60
    minutes = int(value)
    value = (value % 1) * 60
    seconds = int(value)
    if seconds != 0:
        return '%d:%02d:%02d' % (hours, minutes, seconds)
    return '%d:%02d' % (hours, minutes)


@register.filter(name='strftime', expects_localtime=True)
def strftime(value, fmt=None):
    '''
    Format a date/datetime/time using the given format string.
    If no format is given format defaults to the first format
    found in <type>_INPUT_FORMATS.
    '''
    # allow None so you can use mydate|strftime|default:"-"
    if not hasattr(value, 'strftime'):
        return value
    if fmt is None:
        # get_format returns the localized format if USE_L10N=True
        if isinstance(value, datetime.datetime):
            fmt = get_format('DATETIME_INPUT_FORMATS')[0]
        elif isinstance(value, datetime.date):
            fmt = get_format('DATE_INPUT_FORMATS')[0]
        elif isinstance(value, datetime.time):
            fmt = get_format('TIME_INPUT_FORMATS')[0]
        else:
            raise ValueError('No default strftime format for %r' % value)
    return value.strftime(fmt)
