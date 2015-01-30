#!/usr/bin/env python
# vim: set ts=8 sw=4 sts=4 et:
# ======================================================================
# Copyright (C) 2009, Walter Doekes (wdoekes) at OSSO B.V.
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


import re
from . import pyl10n_core as _p
_percent_re = re.compile(r'(%.|[^%]+)')


def teldom2string(phone_tuple, locale=None):
    '''
    See _tel2string help.
    '''
    lc_telephone = _p.localeconv_by_category('LC_TELEPHONE', locale)
    return _tel2string(
        phone_tuple,
        lc_telephone.get('tel_dom_fmt',
                         lc_telephone.get('tel_int_fmt', '+%c %a%t%l')),
        lc_telephone)


def telint2string(phone_tuple, locale=None):
    '''
    See _tel2string help.
    '''
    lc_telephone = _p.localeconv_by_category('LC_TELEPHONE', locale)
    return _tel2string(
        phone_tuple,
        lc_telephone.get('tel_int_fmt', '+%c %a%t%l'),
        lc_telephone)


def _tel2string(phone_tuple, fmt, locale_dict=None):
    '''
    See: ISO/IEC WD 15435

    We do not know the country codes or area codes, so we'll take the phone
    number as a tuple of ([country_code, [area_code,]] local_number). The
    country code shouldn't have any prefixes (like + or 0), nor should the
    area code.

    We don't do anything with int_prefix (country-code) or int_select
    (international-prefix). The nat_select (national-prefix) does not exist
    so we assume it to be 0.

    %a area code without nationwide prefix (prefix is often <0>).
    %A area code including nationwide prefix (prefix is often <0>).
    %l local number (within area code).
    %e extension (to local number)
    %c country code
    %C alternate carrier service code used for dialling abroad
    %t Insert a <space> if the previous descriptor's value was not an empty
       string; otherwise ignore.
    '''
    if len(phone_tuple) == 3:
        country_code, area_code, local_number = (str(i) for i in phone_tuple)
    elif len(phone_tuple) == 2:
        country_code = str(phone_tuple[0])
        area_code = ''
        local_number = str(phone_tuple[1])

    # # Fill in a bit of area code.. two digits sounds about right ;)
    # if area_code == '' and len(local_number) > 3:
    #     area_code, local_number = local_number[0:2], local_number[2:]

    nat_select = '0'

    matches = _percent_re.findall(fmt)
    last = ''
    for i, v in enumerate(matches):
        if v[0] != '%':
            continue
        c = v[1]  # len(v) == 2 according to _percent_re

        if c == '%':
            last = matches[i] = '%'
        elif c == 'a':
            last = matches[i] = area_code
        elif c == 'A':
            last = matches[i] = '%s%s' % (nat_select, area_code)
        elif c == 'l':
            last = matches[i] = local_number
        elif c == 'e':
            raise NotImplementedError('Was not expecting extension in format',
                                      fmt)
        elif c == 'c':
            last = matches[i] = country_code
        elif c == 'C':
            raise NotImplementedError('Was not expecting unknown C in format',
                                      fmt)
        elif c == 't':
            last, matches[i] = '', ('', ' ')[last != '']
        else:
            raise ValueError('Unknown field descriptor in format', fmt)

    return ''.join(matches)


def pyl10n_telephone_test():
    print(teldom2string((31, 50, 1234567), 'en_US'))
    print(telint2string((31, 50, 1234567), 'en_US'))
    print(teldom2string((31, 50, 1234567), 'en_GB'))
    print(telint2string((31, 50, 1234567), 'en_GB'))
    print(teldom2string((31, 50, 1234567), 'nl_NL'))
    print(telint2string((31, 50, 1234567), 'nl_NL'))
    print(teldom2string((31, 50, 1234567), 'sv_SE'))
    print(telint2string((31, 50, 1234567), 'sv_SE'))
