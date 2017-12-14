# vim: set ts=8 sw=4 sts=4 et ai:
import argparse
import optparse

from django import VERSION as django_version
from django.contrib import admin
try:
    from django.contrib.admin.utils import get_deleted_objects
except ImportError:
    from django.contrib.admin.util import get_deleted_objects
try:
    from django.apps import apps
    get_model = apps.get_model
except ImportError:
    from django.db.models import get_model
from django.contrib.contenttypes.models import ContentType
from osso.core.management.base import BaseCommand, CommandError, docstring


class Command(BaseCommand):
    __doc__ = help = docstring("""
    Show or change information about a certain object.

    Supply two+ arguments: app_label.model_name object_pk...
    """)

    # Optparse was used up to Django 1.8.
    if django_version < (1, 8):
        option_list = BaseCommand.option_list + (
            optparse.make_option(
                '--rdepend-count', action='store_true',
                default=False, help='Print count of dependent objects'),
        )

    missing_args_message = 'invalid/missing arguments, see ostat --help'

    def add_arguments(self, parser):
        parser.formatter_class = argparse.RawTextHelpFormatter
        parser.add_argument('model', help='The app_label.model_name')
        parser.add_argument('args', nargs='+', help='The object primary keys')
        parser.add_argument(
            '--rdepend-count', action='store_true',
            default=False, help='Print count of dependent objects')

    def handle(self, *args, **kwargs):
        if 'model' not in kwargs:
            # Convert from optparse to argparse.
            if len(args) < 2:
                raise CommandError(self.missing_args_message)
            args = list(args)
            kwargs['model'] = args.pop(0)

        if '.' not in kwargs['model']:
            raise CommandError('Format model as app_label.model_name')

        app_label, model_name = kwargs['model'].split('.', 1)

        try:
            # Note that old get_model returns None
            model = get_model(app_label, model_name)
        except LookupError:
            model = None

        if model is None:
            if kwargs['model'] == 'django.content_type':
                model = ContentType
            else:
                raise CommandError('No model found: %s' % kwargs['model'])

        if kwargs['rdepend_count']:
            action = self.print_rdepend_count
        else:
            action = self.print_stat

        for object_id in args:
            try:
                object = model.objects.get(pk=object_id)
            except model.DoesNotExist:
                self.stderr.write('%r with pk %r does not exist' %
                                  (model, object_id))
            else:
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
                    retval = get_deleted_objects(
                        (object,), object._meta,
                        AnonymousUser(), AdminSite(), using)

                    if django_version >= (1, 8):
                        (dependent_objects, _, perms_needed,
                         protected) = retval
                    else:
                        (dependent_objects, perms_needed,
                         protected) = retval
                else:
                    (dependent_objects, perms_needed) = \
                        get_deleted_objects((object,), object._meta,
                                            AnonymousUser(), AdminSite())
                object._old_rdepends = False
            else:
                # == GETTING TO_BE_DELETED OBJECTS THE DJANGO 1.1.1- WAY ==
                dependent_objects = [str(object), []]
                perms_needed = set()
                get_deleted_objects(dependent_objects, perms_needed, None,
                                    object, object._meta, 1, admin.site)
                object._old_rdepends = True

            object._rdepends = dependent_objects
        return object._rdepends

    def print_rdepend_count(self, object):
        print((self.count_rdepends(object)))

    def print_stat(self, object):
        dependent_count = self.count_rdepends(object)
        dependent_objects = self.get_rdepends(object)

        if object._old_rdepends:
            def children_print(children, indent=0):
                for child in children:
                    name, grandchildren = child
                    print(('      : %s- %s' % ('  ' * indent, name)))
                    children_print(grandchildren, indent + 1)
        else:
            def children_print(children, indent=0):
                for child in children:
                    if isinstance(child, type([])):
                        children_print(child, indent + 1)
                    else:
                        print(('      : %s- %s' % ('  ' * indent, child)))

        opts = object._meta
        if hasattr(opts, 'module_name'):  # renamed to model_name
            opts.model_name = opts.module_name

        identifier = '%s.%s:%s' % (opts.app_label, opts.model_name, object.pk)
        print(('    ID: %s' % (identifier,)))
        print((' Value: %s' % (str(object),)))
        if hasattr(object, 'created'):
            print(('Create: %s' % (object.created,)))
        if hasattr(object, 'modified'):
            print(('Modify: %s' % (object.modified,)))
        if dependent_count:
            print(('  Deps: %s ==>' % (dependent_count,)))
            if object._old_rdepends:
                children_print(dependent_objects[1])
            else:
                children_print(dependent_objects[1:])
        else:
            print(('  Deps: %s' % (dependent_count,)))
