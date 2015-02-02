#!/bin/sh
# vim: set ts=8 sw=4 sts=4 et ai:
#
# This test script can be used to quickly test Django compatibility with
# your currently loaded virtualenv.

# Jump to base dir, like make(1) would.
cd "`dirname "$0"`"

admin="`which django-admin`"
[ -z "$admin" ] && admin="`which django-admin.py`"
[ -z "$admin" ] && echo 'No virtualenv loaded?' && exit 1

# Apps to test. Exclude:
# - cms because it is a namespace
# - doc because it is no app
# - locale because it is no app
# - xhr because it has no models (nor tests)
APPS=""
OPTS=""
for x in "$@"; do
    case $x in
    -*) OPTS="$OPTS $x";;
    *) APPS="$APPS $x";;
    esac
done
if test -z "$APPS"; then
    APPS="`find osso -maxdepth 1 -type d -name '[A-Za-z0-9]*' |
           sed -e '
               /^osso$/d
               /^osso\/\(cms\|doc\|locale\|xhr\)$/d
               s/^osso\///
           ' | sort`"
fi
APPS="`echo "$APPS" | egrep -v '^(core|relation)$'`"  # included below

cat > osso/test_settings.py << __EOF__
# vim: set ts=8 sw=4 sts=4 et ai:
import os

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': ':memory:',
    }
}

# compat with pre-1.2 django
DATABASE_NAME = DATABASES['default']['NAME']
DATABASE_ENGINE = DATABASES['default']['ENGINE']

LOCALE_PATHS = (os.path.join(os.path.dirname(__file__), 'locale'),)
SECRET_KEY = 50 * 'A'  # must be set to something..

MIDDLEWARE_CLASSES = ()  # avoid Django 1.7 check

INSTALLED_APPS = (
    'django.contrib.auth',
    'django.contrib.contenttypes',
    #'django.contrib.sessions',
    #'django.contrib.sites',
    #'django.contrib.messages',
    #'django.contrib.staticfiles',
    'osso.core',
    'osso.relation',
__EOF__
for app in $APPS; do
    echo "    'osso.$app'," >> osso/test_settings.py
done
cat >> osso/test_settings.py << __EOF__
)

# The l10n middleware likes to have a view to call
try:  # Django 1.4+
    from django.conf.urls import patterns
except ImportError:  # Django 1.3-
    from django.conf.urls.defaults import patterns
from django.http import HttpResponse
def some_view(request):
    return HttpResponse('OK')
ROOT_URLCONF = patterns('',
    (u'^$', some_view),
)

SITE_ID = 1
__EOF__

PYTHONPATH=. "$admin" test --settings=osso.test_settings $OPTS $APPS

# Remove stuff again
rm -f "osso/test_settings.py" "osso/test_settings.pyc"
