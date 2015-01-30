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


import os
try:
    import cPickle as pickle
except:
    import pickle
# set default locale path to ../locale/
_locale_path = os.path.join(os.path.dirname(__file__), '..', 'locale')
# set default locale to C
_current_locale_callable = lambda: 'C'


def setlocale(locale):
    setlocalefunc(lambda: locale)


def setlocalefunc(callable):
    global _current_locale_callable
    _current_locale_callable = callable


def setlocalepath(dirname):
    '''
    Set directory containing message catalogs.

    Message catalogs will be expected at the filename
    dirname/locale/category, where locale is a locale
    name and category is a locale facet such as
    LC_NUMERIC.
    '''
    global _locale_path
    _locale_path = dirname


def localeconv(locale=None):
    locale = locale or _get_locale()
    ret = {}
    ret.update(_get_category(locale, 'LC_MONETARY'))
    ret.update(_get_category(locale, 'LC_NUMERIC'))
    # We've removed trailing zeroes at generation time
    assert 0 not in ret['grouping'] and 0 not in ret['mon_grouping']
    return ret


def localeconv_by_category(category, locale=None):
    locale = locale or _get_locale()
    assert category in (
        'LC_ADDRESS', 'LC_MEASUREMENT', 'LC_MONETARY', 'LC_NAME',
        'LC_NUMERIC', 'LC_PAPER', 'LC_TELEPHONE', 'LC_TIME')
    return _get_category(locale, category)


def _get_category(locale, category):
    if locale not in _get_category._cache:
        _get_category._cache[locale] = {}
    catcache = _get_category._cache[locale]
    if category not in catcache:
        file = None
        try:
            file = open(os.path.join(_locale_path, locale, category), 'rb')
            ret = pickle.load(file)
            assert type(ret) == dict
            catcache[category] = ret
        except Exception as e:
            from sys import stderr
            stderr.write('pyl10n: loading locale category: %s\n' % e)
            catcache[category] = {}
        finally:
            if file is not None:
                file.close()
    return catcache[category]
_get_category._cache = {}


def _get_locale():
    global _current_locale_callable
    return _current_locale_callable()


def pyl10n_core_test():
    # TODO: create tests :)
    pass
