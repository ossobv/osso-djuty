# vim: set ts=8 sw=4 sts=4 et ai tw=79:
from django.contrib.admin.util import NestedObjects


__all__ = ('flatten', 'get_flat_dependencies')


def flatten(list_with_lists):
    # Atom?
    if not (isinstance(list_with_lists, list) or
            isinstance(list_with_lists, tuple)):
        return [list_with_lists]

    # Flatten the list.
    ret = []
    for item in list_with_lists:
        ret.extend(flatten(item))
    return ret


def get_flat_dependencies(object):
    collector = NestedObjects(using='default')
    collector.collect([object])
    to_delete_nested = collector.nested((lambda x: x))
    res = flatten(to_delete_nested)
    if res.pop(0) != object:
        raise AssertionError('Huh?')
    return res
