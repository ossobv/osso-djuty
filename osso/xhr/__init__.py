# vim: set ts=8 sw=4 sts=4 et ai:
from json import JSONEncoder, dumps

from django.conf import settings
from django.db.models.query import QuerySet
from django.http import HttpResponse
from django.utils.encoding import force_text
from django.utils.functional import Promise


class _JsonEncoder(JSONEncoder):
    def default(self, obj):
        if hasattr(obj, 'isoformat'):
            # parsed = new Date(Date.parse(value))
            # https://github.com/csnover/js-iso8601
            return obj.isoformat()
        elif isinstance(obj, QuerySet):
            return list(obj)
        elif isinstance(obj, Promise):
            return force_text(obj)
        return obj


class JsonResponse(HttpResponse):
    '''
    This one is used by clean xmlhttp requests.
    '''
    def __init__(self, request, json_response, compact=False):
        if not isinstance(json_response, str):
            json_kwargs = {
                'check_circular': False,
                'cls': _JsonEncoder,
                'ensure_ascii': False,
                'indent': 2,
                'sort_keys': True,
            }
            if compact or not settings.DEBUG:
                json_kwargs.update({
                    'indent': None, 'separators': (',', ':'),
                    'sort_keys': False})
            json_response = dumps(json_response, **json_kwargs)
        super().__init__(json_response, mimetype='application/json')
