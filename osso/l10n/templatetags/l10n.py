# vim: set ts=8 sw=4 sts=4 et ai:
from django import template
from osso.l10n import locale


register = template.Library()


@register.filter
def lcmon(value, options=''):
    if value in (None, ''):
        return '-'
    kwargs = {
        'dutch_rounding': False or 'd' in options,
        'grouping': True,
        'symbol': False or 's' in options,
    }
    return locale.currency(float(value), **kwargs)
lcmon.is_safe = True # no one uses < > & ' ", right?

@register.filter
def lcnum(value, options=''):
    if value in (None, ''):
        return '-'
    if '%' in options:
        formatstr = options[options.index('%'):]
    else:
        formatstr = '%.12g'
    kwargs = {
        'dutch_rounding': False or 'd' in options,
        'grouping': True,
    }
    return locale.format(formatstr, float(value), **kwargs)
lcnum.is_safe = True # no one uses < > & ' ", right?

@register.filter
def lcdate(value):
    return locale.format_date(value)
lcdate.is_safe = True # no one uses < > & ' ", right?

@register.filter
def lcdatetime(value):
    return locale.format_datetime(value)
lcdatetime.is_safe = True # no one uses < > & ' ", right?

@register.filter
def lctime(value):
    return locale.format_time(value)
lctime.is_safe = True # no one uses < > & ' ", right?
