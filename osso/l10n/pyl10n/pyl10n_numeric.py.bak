#!/usr/bin/env python
# vim: set ts=8 sw=4 sts=4 et:
# ======================================================================
# Copyright (C) 2008,2009, Walter Doekes (wdoekes) at OSSO B.V.
# This file is part of Pyl10n.
#
# Pyl10n is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# Pyl10n is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with Pyl10n.  If not, see <http://www.gnu.org/licenses/>.
# ======================================================================


from . import pyl10n_core as _p


def format(format, val, grouping=False, monetary=False, dutch_rounding=False,
           locale=None):
    if monetary:
        assert format == u'%f'
        return currency(val, False, grouping, dutch_rounding=dutch_rounding,
                        locale=locale)

    assert len(format) and format[0] == u'%'
    conv = _p.localeconv(locale)

    if dutch_rounding:
        val = dutch_round(val, _format_to_fractionals(format))
    ret = format % val
    if u'e' in ret or u'E' in ret:  # we're looking at exponents.. blame user
        return ret
    return _group_and_decimal(ret, grouping, conv['decimal_point'],
                              conv['thousands_sep'], conv['grouping'])


def currency(val, symbol=True, grouping=False, international=False,
             dutch_rounding=False, locale=None):
    conv = _p.localeconv(locale)
    neg = val < 0

    if neg:
        symbol_before = bool(conv['n_cs_precedes'])
        sign = conv['negative_sign']
        sep_by_space = bool(conv['n_sep_by_space'])
        positioning = conv['n_sign_posn']
    else:
        symbol_before = bool(conv['p_cs_precedes'])
        sign = conv['positive_sign']
        sep_by_space = bool(conv['p_sep_by_space'])
        positioning = conv['p_sign_posn']

    if international:
        fractionals = int(conv['int_frac_digits'])

        if symbol:
            if isinstance(symbol, bool):
                symbol_char = conv['int_curr_symbol']
            else:
                symbol_char = symbol
            if len(symbol_char) > 3:
                space_between_symbol_value = symbol_char[3]
            else:
                space_between_symbol_value = ''
            symbol_char = symbol_char[0:3]
    else:
        fractionals = int(conv['frac_digits'])

        if symbol:
            if isinstance(symbol, bool):
                symbol_char = conv['currency_symbol']
            else:
                symbol_char = symbol
            space_between_symbol_value = ('', ' ')[sep_by_space]

    if dutch_rounding:
        val = dutch_round(val, fractionals)
    val = abs(val)
    ret = (u'%%.%if' % fractionals) % val
    ret = _group_and_decimal(ret, grouping, conv['mon_decimal_point'],
                             conv['mon_thousands_sep'], conv['mon_grouping'])

    if not symbol:
        if positioning == 0:
            return u'(%s%s%s)' % (ret,)
        elif positioning == 1 or positioning == 3 or positioning == 127:
            return u'%s%s' % (sign, ret)
        elif positioning == 2 or positioning == 4:
            return u'%s%s' % (ret, sign)
        assert False

    if symbol_before:
        args = [symbol_char, space_between_symbol_value, ret]
    else:
        args = [ret, space_between_symbol_value, symbol_char]

    if positioning == 0:
        ret = u'(%s%s%s)' % tuple(args)
    else:
        if (positioning == 1 or (positioning == 3 and symbol_before) or
                positioning == 127):
            args.insert(0, sign)
        elif positioning == 2 or (positioning == 4 and not symbol_before):
            args.append(sign)
        elif positioning == 3:
            args.insert(2, sign)
        elif positioning == 4:
            args.insert(1, sign)
        else:
            assert False
        ret = u'%s%s%s%s' % tuple(args)

    return ret


def atof(string, allow_grouping=True, func=float, locale=None):
    conv = _p.localeconv(locale)
    if allow_grouping:
        ts = conv['thousands_sep']
        ds = conv['decimal_point']
        if u'.' in string and u'.' not in (ts, ds):
            raise ValueError('invalid decimal separator found')
        string = string.replace(ts, u'')  # get rid of grouping (ignore pos)
    else:
        ds = conv['decimal_point']
        if u'.' in string and u'.' != ds:
            raise ValueError('invalid decimal separator found')
    if ds != u'':
        string = string.replace(ds, u'.')
    return func(string)


def atoi(string, *args, **kwargs):
    kwargs['func'] = int
    return atof(string, *args, **kwargs)


def dutch_round(val, fractionals):
    for i in range(fractionals):
        val *= 10.0
    leftovers = round(val % 1, 4)  # round because float fluctuates
    if leftovers == 0.5:
        val = int(round(val, 4))
        if val % 2 == 1:
            val += (1, -1)[val < 0]
    else:
        val = round(val, 0)
    for i in range(fractionals):
        val /= 10.0
    return val


def str(val, locale=None):
    return format('%.12g', val, locale=locale)


def _format_to_fractionals(format):
    try:
        i = format.index('.')
        for j in range(i + 1, len(format)):
            if format[j] not in '0123456789':
                fractionals = int(format[(i + 1):j])
                break
        else:
            fractionals = int(fractionals[i + 1])
    except ValueError:
        fractionals = 0
    return fractionals


def _group(val, group_char, group_list):
    if val[0] not in '0123456789':
        sign = val[0]
        val = val[1:]
    else:
        sign = ''

    ret = []
    i = len(val)
    # group_list defines grouping from right to left
    group = 127
    for group in group_list:
        if i <= 0 or group == 127:  # CHAR_MAX => no more grouping
            break
        # append next group to list
        ret.insert(0, val[max(0, i - group):i])
        i -= group
    # continue with last value from group_list
    while i > 0:
        ret.insert(0, val[max(0, i - group):i])
        i -= group
    # concat and return
    return sign + group_char.join(ret)


def _group_and_decimal(val, grouping, decimal_char, group_char, group_list):
    if grouping:
        if u'.' in val:
            left, right = val.split(u'.')
            return u'%s%s%s' % (_group(left, group_char, group_list),
                                decimal_char, right)
        else:
            return _group(val, group_char, group_list)
    return val.replace(u'.', decimal_char)


def pyl10n_numeric_test():
    # TODO: create tests :)
    pass
