# vim: set ts=8 sw=4 sts=4 et ai:
import optparse

from django import VERSION as django_version
from django.contrib import admin
from django.contrib.admin.util import get_deleted_objects
from django.contrib.contenttypes.models import ContentType
from django.core.exceptions import ObjectDoesNotExist
from django.db import models
from osso.core.management.base import BaseCommand, CommandError, docstring


class Command(BaseCommand):
    __doc__ = help = docstring("""
    Show or change information about a certain object.

    Supply two+ arguments: app_label.model_name object_pk...
    """)

    option_list = BaseCommand.option_list + (
        optparse.make_option('--rdepend-count', action='store_true',
            default=False, help='Print count of dependent objects'),
    )

    def handle(self, *args, **kwargs):
        try:
            assert len(args) >= 2 and '.' in args[0], \
                'Need (only) object type and object pk arguments'
            app_label, model_name = args[0].split('.', 1)
            model = models.get_model(app_label, model_name)
            assert model, ('No model found for app_label %s, model_name %s' %
                           (app_label, model_name))
        except (AssertionError, IndexError, ObjectDoesNotExist) as e:
            if args[0] == 'django.content_type':
                model = ContentType
            else:
                raise CommandError('No object found: %s' %
                                   (': '.join(unicode(i) for i in e.args),))

        if kwargs.get('rdepend_count', False):
            action = self.print_rdepend_count
        else:
            action = self.print_stat

        for object_id in args[1:]:
            object = model.objects.get(pk=object_id)
            action(object)

    def count_rdepends(self, object):
        deps = self.get_rdepends(object)

        if object._old_rdepends:
            def children_count(list):
                ret = 0
                name, children = list
                for child in children:
                    ret += 1 + children_count(child)
                return ret
            return children_count(deps)
        else:
            def children_count(list):
                ret = 0
                for child in list:
                    if isinstance(child, type([])):
                        ret += children_count(child)
                    else:
                        ret += 1
                return ret
            return children_count(deps[1:])

    def get_rdepends(self, object):
        if not hasattr(object, '_rdepends'):
            if django_version >= (1, 1, 4):
                # == GETTING TO_BE_DELETED OBJECTS THE DJANGO 1.1.4+ WAY ==
                class AnonymousUser:
                    is_staff = is_superuser = False

                    def has_perm(self, perm):
                        return False

                # Hacks to force has_admin=False
                class AdminSite:
                    name = 'irrelevant'
                    _registry = {}

                if django_version >= (1, 3):
                    using = 'default'
                    (dependent_objects, perms_needed, protected) = \
                        get_deleted_objects((object,), object._meta,
                                            AnonymousUser(), AdminSite(),
                                            using)
                else:
                    (dependent_objects, perms_needed) = \
                        get_deleted_objects((object,), object._meta,
                                            AnonymousUser(), AdminSite())
                object._old_rdepends = False
            else:
                # == GETTING TO_BE_DELETED OBJECTS THE DJANGO 1.1.1- WAY ==
                dependent_objects = [unicode(object), []]
                perms_needed = set()
                get_deleted_objects(dependent_objects, perms_needed, None,
                                    object, object._meta, 1, admin.site)
                object._old_rdepends = True

            object._rdepends = dependent_objects
        return object._rdepends

    def print_rdepend_count(self, object):
        print(self.count_rdepends(object))

    def print_stat(self, object):
        dependent_count = self.count_rdepends(object)
        dependent_objects = self.get_rdepends(object)

        if object._old_rdepends:
            def children_print(children, indent=0):
                for child in children:
                    name, grandchildren = child
                    print('      : %s- %s' % ('  ' * indent, name))
                    children_print(grandchildren, indent + 1)
        else:
            def children_print(children, indent=0):
                for child in children:
                    if isinstance(child, type([])):
                        children_print(child, indent + 1)
                    else:
                        print('      : %s- %s' % ('  ' * indent, child))

        opts = object._meta

        identifier = '%s.%s:%s' % (opts.app_label, opts.module_name, object.pk)
        print('    ID: %s' % (identifier,))
        print(' Value: %s' % (unicode(object),))
        if hasattr(object, 'created'):
            print('Create: %s' % (object.created,))
        if hasattr(object, 'modified'):
            print('Modify: %s' % (object.modified,))
        if dependent_count:
            print('  Deps: %s ==>' % (dependent_count,))
            if object._old_rdepends:
                children_print(dependent_objects[1])
            else:
                children_print(dependent_objects[1:])
        else:
            print('  Deps: %s' % (dependent_count,))
