#!/usr/bin/env python
import os
import subprocess
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
            packages.append(new_root.replace('/', '.'))

    for file in files:
        if (os.path.splitext(file)[1] in ('.html', '.xml', '.js',
                                          '.po', '.mo', '.diff') or
                file in ('COPYING', 'README', 'Makefile') or
                file.startswith('LC_')):  # LC_locale_stuff
            # Drop osso/ when appending.
            data.append(os.path.join(new_root, file)[5:])

# Remove some?
packages = [i for i in packages if not i.startswith('osso.cms')]
data = [i for i in data if not i.startswith('cms/')]  # relative to osso/
packages = [i for i in packages if not i.startswith('osso.search')]
data = [i for i in data if not i.startswith('search/')]  # relative to osso/
# packages = [i for i in packages if not i.startswith('osso.sms')]
# data = [i for i in data if not i.startswith('sms/')]


# Add versioning; it's PEP386 compatible with:
# <major>.<minor>.<timestamp_as_micro>-<git_version>
version_path = os.path.join(os.path.dirname(__file__), 'osso', '.version')
try:
    # sdist gets to save the version.
    version = subprocess.check_output([
        'git', 'log', '-1', '--pretty=format:0.9.%ct-%h'])
except subprocess.CalledProcessError:
    # install gets to look it up.
    file_ = open(version_path)
    version = file_.read().strip()
    file_.close()
else:
    file_ = open(version_path, 'w')
    file_.write('%s\n' % (version,))
    file_.close()
data.append('.version')


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
        # plen = len(src_dir)+1
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
    version=version,
    # Which files?
    packages=packages,
    package_data={'osso': data},  # cheat and let all data belong to osso pkg
    data_files=(),
    # Descriptions.
    description='OSSO-Djuty Django utility lib',
    long_description=('Various useful tools, partly used for development '
                      'with Django and partly useful without.'),
    author='OSSO B.V.',
    author_email='info+osso-djuty@osso.nl',
    url='https://github.com/ossobv/osso-djuty',
    # license='Unknown',
    # platforms=('linux',),
    # classifiers=[
    #     'Development Status :: 4 - Beta',
    #     'Intended Audience :: Developers',
    #     ('License :: OSI Approved :: GNU General Public License v3 or later '
    #      '(GPLv3+)'),
    #     'Operating System :: MacOS :: MacOS X',
    #     'Operating System :: POSIX :: Linux',
    #    'Programming Language :: Python :: 2',
    #     'Topic :: Software Development :: Libraries',
    # ],
)

# vim: set ts=8 sw=4 sts=4 et ai tw=79:
