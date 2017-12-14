#!/usr/bin/env python
# Copyright (C) 2008,2009, OSSO B.V.
# vim: set ts=8 sw=4 sts=4 et:
#=======================================================================
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
#=======================================================================


# INTRODUCTION
# ============
# Pyl10n is a thread-safe /locale module/ replacement. Most functions
# behave very similarly to their locale.* counterparts.
#
# Load this file (__init__.py) to get all functionality, e.g.:
# {{{
# import path.to.pyl10n as locale
# }}}
#
# The functions that are currently implemented are the following, the
# (+) marks functions that are not found in the regular locale module.
# Most functions will also accept an optional callable that returns the
# current locale.
#
# FILE pyl10n_core:
#  * localeconv
#  * localeconv_by_category (+)
#  * setlocale
#  * setlocalefunc (+)
#  * setlocalepath (+)
#
# FILE pyl10n_numeric
#  * atof
#  * atoi
#  * currency
#  * dutch_round (+)
#  * format
#  * str
#
# FILE pyl10n_telephone
#  * teldom2string (+)
#  * telint2string (+)
#
# FILE pyl10n_time
#  * format_date (+)
#  * format_datetime (+)
#  * format_time (+)
#  * strftime


# QUICK HOWTO
# ===========
# Before using pyl10n, make sure that the path in pyl10n_core is set up
# correctly for your file layout. Edit the following statement to fit
# your needs:
# {{{
# _locale_path = os.path.join(os.path.dirname(__file__), '..', 'locale')
# }}}
#
# Using pyl10n like locale:
# {{{
# import path.to.pyl10n as locale
# locale.setlocale('nl_NL')
# print(locale.currency(12345.67))
# }}}
#
# Using pyl10n in your threaded app:
# {{{
# import path.to.pyl10n as locale, datetime
# locale.setlocalefunc(some_func_that_returns_locale_for_current_thread)
# print(locale.format_time(datetime.datetime.now()))
# }}}
#
# Quickly switching languages:
# {{{
# import path.to.pyl10n as locale, datetime
# now = datetime.datetime.now()
# print(locale.format_time(now, 'nl_NL'))
# print(locale.format_time(now, 'en_US'))
# }}}


# DIFFERENCES WITH LOCALE
# =======================
# The following differences with the original locale module should be
# observed:
#  * Use only the language/region when specifying the locale.
#    E.g.: ('nl_NL') instead of (LC_NUMERIC, 'nl_NL.UTF-8').
#  * Pyl10n does not load variables like DAY_1 etc. in the global
#    context. You can get them from localeconv_by_category if you need
#    them. (See the pyl10n_time functions for quick shortcuts.)
#  * Python is inconsistent with stripping or not stripping trailing
#    zeroes from lists in locale definitions. Pyl10ngen always strips
#    trailing zeroes.
#  * Extended currency to accept a non-boolean for symbol that will be
#    used as the currency symbol, e.g. currency='EUR '.


# BUGS / MISSING FEATURES
# =======================
# The following things are missing from pyl10n:
#  * Proper regression tests are not done yet.
#  * Address/telephone formatting functions are still missing or very
#    rudimentary.
#  * The locale path is 'hardcoded' relative to __file__ in this file.
#  * The standard is unclear about how to handle [np]_sep_by_space for
#    international sumbols. We assume that the space is an optional
#    fourth character in int_curr_symbol. See
#    http://bugs.python.org/issue1222 for more information.
#  * format(...monetary=True) gets handled by currency(). This means
#    that your format string will be ignored.
#  * Replace 'category' with 'facet' perhaps?
#  * Document setlocalepath (and link its usage to bindtextomain(3))


# WON'T BE IMPLEMENTED
# ====================
# The following things will not be implemented at all:
#  * Character type and collation functions will not be implemented
#    (e.g. strcoll, strxfrm, format_string).
#  * string.letters is not modified when calling setlocale(). (See the
#    previous point.)


from .pyl10n_core import *
from .pyl10n_numeric import *
from .pyl10n_telephone import *
from .pyl10n_time import *


def pyl10n_old_test():
    import __builtin__, locale, sys

    for lang in ('nl_NL', 'en_US'):
        print(u'**** %s ****\n' % (lang,))
        try:
            locale.setlocale(locale.LC_MONETARY, lang + '.utf-8')
            locale.setlocale(locale.LC_NUMERIC, lang + '.utf-8')
        except locale.Error:
            raise ValueError('Need %s.utf-8 locale for this test. Please "apt-get install '
                             'language-pack-nl" or similar..' % (lang,))
        setlocale(lang)

        print(u'%24s|%24s' % ('[locale]', '[pyl10n]'))
        lconv = locale.localeconv()
        pconv = localeconv()
        keys = lconv.keys()
        keys.sort()
        for k in keys:
            print(u'%24s|%24s <= %s' % (__builtin__.str(lconv[k]).decode('utf-8'), pconv[k], k))
        print()

        print('%24s|%24s' % ('[locale]', '[pyl10n]'))

        print('%24s|%24s' % (locale.str(-3.1415), str(-3.1415)))
        for val in (0.7, -0.7, 1234567.89, -1234567.89):
            for monetary in (False, True):
                lval = locale.format('%f', val, True, monetary).decode('utf-8')
                pval = format('%f', val, True, monetary)
                if not monetary:
                    assert val == locale.atof(lval) and val == atof(pval), \
                            'atof() is broken on value \'%s\'' % (val,)
                print('%24s|%24s' % (lval, pval))
        for val in (0.7, -0.7, 1234567.89, -1234567.89):
            for intl in (False, True):
                lval = locale.currency(val, True, True, intl).decode('utf-8')
                pval = currency(val, True, True, intl)
                print('%24s|%24s' % (lval, pval))
        print

        if lang == 'nl_NL':
            assert atof('1012,34', allow_grouping=True) == 1012.34
            try: atof('123.000', allow_grouping=False)
            except: pass
            else: assert False, 'atof() should\'ve raised an exception'
        elif lang == 'en_US':
            assert atof('1,012.34', allow_grouping=True) == 1012.34
            try: atof('123,000', allow_grouping=False)
            except: pass
            else: assert False, 'atof() should\'ve raised an exception'

        print('All available locale data:')
        for cat in ('LC_ADDRESS', 'LC_MEASUREMENT', 'LC_MONETARY', \
                'LC_NAME', 'LC_NUMERIC', 'LC_PAPER', 'LC_TELEPHONE', 'LC_TIME'):
            print('   %s' % (localeconv_by_category(cat),))
        print


if __name__ == '__main__':
    import codecs, locale, sys
    sys.stdout = codecs.getwriter(locale.getdefaultlocale()[1])(sys.stdout, 'replace')

    pyl10n_core_test()
    pyl10n_numeric_test()
    pyl10n_telephone_test()
    pyl10n_time_test()

    pyl10n_old_test()
