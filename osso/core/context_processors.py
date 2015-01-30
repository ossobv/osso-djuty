# vim: set ts=8 sw=4 sts=4 et ai:
from django.conf import settings


__all__ = ('installed_apps', 'project')


def installed_apps(request):
    return {
        'INSTALLED_APPS': settings.INSTALLED_APPS,
    }


def project(request):
    return {
        'PROJECT_VERSION': settings.PROJECT_VERSION,
    }
