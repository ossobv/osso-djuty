# vim: set ts=8 sw=4 sts=4 et ai:
from django.utils.functional import SimpleLazyObject
from osso.userchat.models import Channel

try:
    # Django 1.4+
    from django.utils.functional import empty
except ImportError:
    # Django 1.3-
    empty = None


class NotSoSimpleLazyObject(SimpleLazyObject):
    def __iter__(self):
        if self._wrapped is empty:
            self._setup()
        return iter(self._wrapped)

    def __len__(self):
        if self._wrapped is empty:
            self._setup()
        return len(self._wrapped)


def userchat(request):
    # See the django.contrib.auth context processor notes about why
    # we're using a lazy object.
    def get_userchat_channels():
        try:
            relation = request.active_relation
        except AttributeError:
            relation = request.user.get_profile().relation
        groups = request.user.groups.all()
        return list(Channel.objects.filter(relation=relation,
                                           groups__in=groups).distinct())

    return {
        'userchat_channels': NotSoSimpleLazyObject(get_userchat_channels),
    }
