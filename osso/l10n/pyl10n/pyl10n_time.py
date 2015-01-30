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


import re
import time
from . import pyl10n_core as _p
_percent_re = re.compile(r'(%.|[^%]+)')  # misses modifiers (like %Ey)


def format_date(date, locale=None):
    lc_time = _p.localeconv_by_category('LC_TIME', locale)
    return _strftime(lc_time['d_fmt'], lc_time, date)


def format_datetime(date, locale=None):
    lc_time = _p.localeconv_by_category('LC_TIME', locale)
    return _strftime(lc_time['d_t_fmt'], lc_time, date)


def format_time(date, locale=None):
    lc_time = _p.localeconv_by_category('LC_TIME', locale)
    return _strftime(lc_time['t_fmt'], lc_time, date)


def strftime(fmt, date=None, locale=None):
    if date is None:
        import datetime
        date = datetime.datetime.now()
    lc_time = _p.localeconv_by_category('LC_TIME', locale)
    return _strftime(fmt, lc_time, date)


def _strftime(fmt, lc_time, date=None):
    lt = date.timetuple()  # local time

    matches = _percent_re.findall(fmt)
    for i, v in enumerate(matches):
        if v[0] != '%':
            continue
        c = v[1]  # len(v) == 2 according to _percent_re

        if c == '%': matches[i] = '%'
        elif c == 'a': matches[i] = lc_time['abday'][(lt[6] + 1) % 7]
        elif c == 'A': matches[i] = lc_time['day'][(lt[6] + 1) % 7]
        elif c == 'b' or c == 'h': matches[i] = lc_time['abmon'][lt[1] - 1]
        elif c == 'B': matches[i] = lc_time['mon'][lt[1] - 1]
        elif c == 'c': matches[i] = _strftime(lc_time['d_t_fmt'], lc_time,
                                              date)
        elif c == 'C': matches[i] = '%02d' % (lt[0] / 100)
        elif c == 'd': matches[i] = '%02d' % lt[2]
        elif c == 'D': matches[i] = ('%02d/%02d/%02d' %
                                     (lt[1], lt[2], lt[0] % 100))
        elif c == 'e': matches[i] = '%2d' % lt[2]
        # %E => modifier, not implemented
        elif c == 'F': matches[i] = '%d-%02d-%02d' % (lt[0], lt[1], lt[2])
        # %G => NOT IMPLEMENTED
        # %g => NOT IMPLEMENTED
        elif c == 'H': matches[i] = '%02d' % lt[3]
        elif c == 'I': matches[i] = '%02d' % (((lt[3] + 11) % 12) + 1)
        elif c == 'j': matches[i] = '%03d' % lt[7]
        elif c == 'k': matches[i] = '%2d' % lt[3]
        elif c == 'l': matches[i] = '%2d' % (((lt[3] + 11) % 12) + 1)
        elif c == 'm': matches[i] = '%02d' % lt[1]
        elif c == 'M': matches[i] = '%02d' % lt[4]
        elif c == 'n': matches[i] = '\n'
        # %O => modifier, not implemented
        elif c == 'p': matches[i] = lc_time['am_pm'][lt[3] >= 12]
        elif c == 'P': matches[i] = lc_time['am_pm'][lt[3] >= 12].lower()  # (GNU)
        elif c == 'r': matches[i] = _strftime(lc_time['t_fmt_ampm'], lc_time,
                                              date)
        elif c == 'R': matches[i] = '%02d-%02' % (lt[3], lt[4])
        elif c == 's': matches[i] = str(time.mktime(date.utcnow()))
        elif c == 'S': matches[i] = '%02d' % lt[5]
        elif c == 't': matches[i] = '\t'
        elif c == 'T': matches[i] = '%02d:%02d:%02d' % (lt[3], lt[4], lt[5])
        elif c == 'u': matches[i] = str(lt[6] + 1)
        # %U => NOT IMPLEMENTED
        # %V => NOT IMPLEMENTED
        elif c == 'w': matches[i] = str((lt[6] + 1) % 7)
        # %W => NOT IMPLEMENTED
        elif c == 'x': matches[i] = _strftime(lc_time['d_fmt'], lc_time, date)
        elif c == 'X': matches[i] = _strftime(lc_time['t_fmt'], lc_time, date)
        elif c == 'y': matches[i] = '%02d' % (lt[0] % 100)
        elif c == 'Y': matches[i] = str(lt[0])
        # %z => NOT IMPLEMENTED # (GNU)
        # %Z => NOT IMPLEMENTED
        elif c == 'z' or c == 'Z': matches[i] = ''  # BROKEN, NOT IMPLEMENTED
        # %+ => NOT IMPLEMENTED

    return ''.join(matches).strip()


def pyl10n_time_test():
    import datetime
    now = datetime.datetime.now()
    print(format_datetime(now - datetime.timedelta(minutes=5), 'de_DE'))
    print(format_datetime(now - datetime.timedelta(minutes=10), 'en_US'))
    print(format_datetime(now - datetime.timedelta(minutes=15), 'nl_NL'))
    print(format_datetime(now - datetime.timedelta(minutes=20), 'sv_SE'))
