# vim: set ts=8 sw=4 sts=4 et ai:
from django.apps import apps as django_apps
from django.utils.functional import SimpleLazyObject

from osso.sequence.backends import SequenceDoesNotExist, SequenceError

__all__ = ['SequenceDoesNotExist', 'SequenceError', 'sequence']

default_app_config = 'osso.sequence.apps.SequenceAppConfig'


def _get_backend():
    return django_apps.get_app_config('sequence').get_backend()


sequence = SimpleLazyObject(_get_backend)
