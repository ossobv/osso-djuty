# vim: set ts=8 sw=4 sts=4 et ai:


class LazyActiveRelation(object):
    def __get__(self, request, obj_type=None):
        if not hasattr(request, '_cached_active_relation'):
            from osso.relation.utils import get_active_relation
            request._cached_active_relation = get_active_relation(request)
        return request._cached_active_relation


class LazyActiveRelationId(object):
    def __get__(self, request, obj_type=None):
        if not hasattr(request, '_cached_active_relation_id'):
            from osso.relation.utils import get_active_relation
            if hasattr(request, '_cached_active_relation'):
                request._cached_active_relation_id = request._cached_active_relation
            else:
                relation = get_active_relation(request, allow_id=True)
                if isinstance(relation, int):
                    request._cached_active_relation_id = relation
                else:
                    request._cached_active_relation = relation
                    request._cached_active_relation_id = relation.id
        return request._cached_active_relation_id


class ActiveRelationMiddleware(object):
    def process_request(self, request):
        # If we do assert hasattr(request, "user") here, we "execute" it
        # and that costs us a query even when we don't need it, so we
        # skip that.
        request.__class__.active_relation = LazyActiveRelation()
        request.__class__.active_relation_id = LazyActiveRelationId()
        return None
