# vim: set ts=8 sw=4 sts=4 et ai:
from django.conf import settings
from django.contrib.auth.management import (
    create_permissions, _get_all_permissions)
from django.db.models import get_models
from django.db.models.signals import post_syncdb
try:
    from django.utils.encoding import smart_text
except ImportError:
    from django.utils.encoding import smart_unicode as smart_text


def create_permissions_respecting_proxy(app, created_models, verbosity,
                                        **kwargs):
    '''
    An alternative to create_permissions found in django.contrib.auth.
    This one doesn't use the ContentType.objects.get_for_model which
    resolves the klass to the base model. Instead it returns the
    content type for the proxy model.
    '''
    from django.contrib.contenttypes.models import ContentType
    from django.contrib.auth.models import Permission
    app_models = get_models(app)
    if not app_models:
        return
    for klass in app_models:
        # The difference is here:
        # ctype = ContentType.objects.get_for_model(klass)
        opts = klass._meta
        ctype, created = ContentType.objects.get_or_create(
            app_label=opts.app_label,
            model=opts.object_name.lower(),
            defaults={'name': smart_text(opts.verbose_name_raw)},
        )
        # (end of difference)
        for codename, name in _get_all_permissions(klass._meta):
            p, created = Permission.objects.get_or_create(
                codename=codename, content_type__pk=ctype.id,
                defaults={'name': name, 'content_type': ctype})
            if created and verbosity >= 2:
                print("Adding permission '%s'" % p)


# Replace the original handling with our modified one if
# CONTENTTYPE_NO_TRAVERSE_PROXY is set.
# This is needed if you want to use proper permissions for proxy models
# that are tied to the proxy application.
# See also: http://code.djangoproject.com/ticket/11154
try:
    settings.CONTENTTYPE_NO_TRAVERSE_PROXY
except AttributeError:
    pass
else:
    if settings.CONTENTTYPE_NO_TRAVERSE_PROXY:
        post_syncdb.disconnect(
            create_permissions,
            dispatch_uid='django.contrib.auth.management.create_permissions')
        post_syncdb.connect(
            create_permissions_respecting_proxy,
            dispatch_uid='django.contrib.auth.management.create_permissions')
