# vim: set ts=8 sw=4 sts=4 et ai:
from django import template


register = template.Library()


@register.filter
# convert the value to a string (XXX docs/tests)
def str(value):
    return str(value)


@register.filter
# truncate after a certain number of characters (XXX docs/tests)
def truncchar(value, arg):
    if not isinstance(value, str):
        value = str(value)
    if len(value) <= arg:
        return value
    else:
        return value[:arg] + '...'
