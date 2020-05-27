#!/usr/bin/env python
# -*- coding: utf-8 -*-
import os
from subprocess import CalledProcessError, check_output

from setuptools import setup, find_packages

# Add versioning; it's PEP386 compatible with:
# <major>.<minor>.<timestamp_as_micro>-<git_version>
version_path = os.path.join(os.path.dirname(__file__), 'osso', '.version')
try:
    # sdist gets to save the version.
    version = check_output([
        'git', 'log', '-1', '--pretty=format:0.9+%ct.%h']).decode()
except (CalledProcessError, FileNotFoundError):
    # install gets to look it up.
    try:
        with open(version_path) as f:
            version = f.read().strip()
    except FileNotFoundError:
        version = '0.9'  # Fallback for source tar downloads.
else:
    with open(version_path, 'w') as f:
        f.write('%s\n' % (version,))

setup(
    # In need of a better name.
    name='osso-djuty',
    version=version,
    packages=find_packages(include=['osso', 'osso.*']),
    include_package_data=True,
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
    install_requires=[
        'pyl10n>=1.0',
    ],
)

# vim: set ts=8 sw=4 sts=4 et ai tw=79:
