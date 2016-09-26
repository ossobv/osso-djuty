# Conditional includes that require Django to be loaded.
# We can run the tests without these.
import os

try:
    from django.conf import settings

    # The settings object is lazy. It will attempt to access the
    # DJANGO_SETTINGS_MODULE first when the first entry is tried.
    # We don't want to break the laziness by trying something here, but
    # we need to know if the lookup will fail. Check the required
    # environment variable.
    try:
        os.environ['DJANGO_SETTINGS_MODULE']
    except KeyError:
        raise ImportError('DJANGO_SETTINGS_MODULE undefined')
except ImportError:
    settings = None
    mail_admins = (lambda *args, **kwargs: None)
    reverse = None

    aboutconfig = None
    log = (lambda *args, **kwargs: None)
else:
    from django.core.mail import mail_admins  # noqa
    from django.core.urlresolvers import reverse  # noqa

    from osso.autolog.utils import log  # noqa
    from osso.aboutconfig.utils import aboutconfig  # noqa


try:  # Django 1.4+
    from django.conf.urls import patterns, url  # noqa
except ImportError:  # Django 1.3-
    from django.conf.urls.defaults import patterns, url  # noqa
