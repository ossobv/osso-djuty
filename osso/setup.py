#!/usr/bin/env python
import os
from distutils.core import setup


# Browse packages.
packages = []
datafiles = []
data = []
striplen = None
for root, dirs, files in os.walk(os.path.dirname(__file__) or '.'):
    if striplen is None:
        if not root:
            striplen = 0
        else:
            striplen = len(root) + 1  # root + dirsep

    new_root = root[striplen:]
    if '__init__.py' in files:
        if '.' not in new_root:
            packages.append('osso.' + new_root.replace('/', '.'))

    for file in files:
        if (os.path.splitext(file)[1] in ('.html', '.xml', '.js',
                                          '.po', '.mo', '.diff') or
            file in ('COPYING', 'README', 'Makefile') or
            file.startswith('LC_')):  # LC_locale_stuff
            data.append(os.path.join(new_root, file))

# Remove some?
packages = [i for i in packages if not i.startswith('osso.cms')]
data = [i for i in data if not i.startswith('cms/')]
packages = [i for i in packages if not i.startswith('osso.search')]
data = [i for i in data if not i.startswith('search/')]
#packages = [i for i in packages if not i.startswith('osso.sms')]
#data = [i for i in data if not i.startswith('sms/')]


#####################
# HACKS BEGIN HERE! #
#####################
# Otherwise we get these errors:
# """error: can't copy 'seractivity/fixtures/config_data.xml': doesn't exist or
#    not a regular file""" when it wants to copy stuff from "useractivity".
from setuptools.command.build_py import build_py


def _get_data_files_HACK(self):
    """Generate list of '(package,src_dir,build_dir,filenames)' tuples"""
    self.analyze_manifest()
    data = []
    for package in self.packages or ():
        # Locate package source directory
        src_dir = self.get_package_dir(package)

        # Compute package build directory
        build_dir = os.path.join(*([self.build_lib] + package.split('.')))

        # Length of path to strip from found files
        # FIX IS HERE!
        #plen = len(src_dir)+1
        if src_dir:
            plen = len(src_dir) + 1
        else:
            plen = 0

        # Strip directory from globbed filenames
        filenames = [
            file[plen:] for file in self.find_data_files(package, src_dir)
        ]
        data.append((package, src_dir, build_dir, filenames))
    return data

# HEY WAIT! Wasn't this bug reported in April 2005??
# http://mail.python.org/pipermail/distutils-sig/2005-April/004458.html
# http://permalink.gmane.org/gmane.comp.python.distutils.devel/1589
build_py._get_data_files = _get_data_files_HACK
###################
# HACKS END HERE! #
###################


setup(
    # In need of a better name.
    name='osso-djuty',
    # Trying to use a PEP386 and distutils.version.StrictVersion compatible
    # versioning scheme here: 0.2a sorts before 0.2 and will mean
    # not-exactly-0.2-yet.
    version='0.0.1a',  # perpetual dev-mode
    # Put everything in the "osso" dir. We may want to rename that at some
    # point.
    package_dir={'osso': ''},
    packages=packages,
    package_data={'': data + [
        'core/middleware-fail2ban.diff',
        'core/tests-data/to_linear_text.html',
        'core/tests-data/to_linear_text.txt',
        'sms/sql/textmessage.mysql.sql',
        'sms/sql/textmessage.postgresql_psycopg2.sql',
    ]},
    # Explicitly set to empty, but that doesn't matter. It breaks anyway :(
    data_files=(),
    description='OSSO-Djuty Django utility lib',
    long_description=('Various useful tools, partly used for development '
                      'with Django and partly useful without.'),
    author='OSSO B.V.',
    author_email='info+osso-djuty@osso.nl',
    url='https://github.com/ossobv/osso-djuty',
    #license='Unknown',
    #platforms=('linux',),
    #classifiers=[
    #    'Development Status :: 4 - Beta',
    #    'Intended Audience :: Developers',
    #    ('License :: OSI Approved :: GNU General Public License v3 or later '
    #     '(GPLv3+)'),
    #    'Operating System :: MacOS :: MacOS X',
    #    'Operating System :: POSIX :: Linux',
    #    'Programming Language :: Python :: 2',
    #    'Topic :: Software Development :: Libraries',
    #],
)

# vim: set ts=8 sw=4 sts=4 et ai tw=79:
