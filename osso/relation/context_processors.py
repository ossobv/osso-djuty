# vim: set ts=8 sw=4 sts=4 et ai:
from django.utils.functional import SimpleLazyObject


def relation(request):
    # See the django.contrib.auth context processor notes about why
    # we're using a lazy object.
    def get_active_relation():
        if hasattr(request, 'active_relation'):
            return request.active_relation
        return None

    return {
        'active_relation': SimpleLazyObject(get_active_relation),
    }
