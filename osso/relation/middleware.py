# vim: set ts=8 sw=4 sts=4 et ai:
from osso.relation.utils import get_active_relation


class LazyActiveRelation(object):
    def __get__(self, request, obj_type=None):
        if not hasattr(request, '_cached_active_relation'):
            relation = get_active_relation(request)
            request._cached_active_relation = relation
            request._cached_active_relation_id = getattr(relation, 'pk', None)
        return request._cached_active_relation


class LazyActiveRelationId(object):
    def __get__(self, request, obj_type=None):
        if not hasattr(request, '_cached_active_relation_id'):
            relation = get_active_relation(request)
            request._cached_active_relation = relation
            request._cached_active_relation_id = getattr(relation, 'pk', None)
        return request._cached_active_relation_id


class ActiveRelationMiddleware(object):
    def process_request(self, request):
        # If we do assert hasattr(request, "user") here, we "execute" it
        # and that costs us a query even when we don't need it, so we
        # skip that.
        request.__class__.active_relation = LazyActiveRelation()
        request.__class__.active_relation_id = LazyActiveRelationId()
        return None
