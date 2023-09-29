# vim: set ts=8 sw=4 sts=4 et ai:
from json import JSONEncoder, dumps

from django.template import Library
from django.utils.encoding import force_str
from django.utils.functional import Promise

register = Library()


class _JSONEncoder(JSONEncoder):
    def default(self, obj):
        if isinstance(obj, Promise):
            return force_str(obj)
        return obj


@register.filter
def json(input):
    return dumps(input, ensure_ascii=False, check_circular=False,
                 cls=_JSONEncoder)
