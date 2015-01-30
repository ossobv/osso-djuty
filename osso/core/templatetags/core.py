# vim: set ts=8 sw=4 sts=4 et ai:
import decimal
from django import template


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
