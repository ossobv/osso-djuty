# vim: set ts=8 sw=4 sts=4 et ai:
import argparse

from django.contrib.admin.utils import get_deleted_objects
from django.apps import apps
from django.contrib.contenttypes.models import ContentType
from osso.core.management.base import BaseCommand, CommandError, docstring

get_model = apps.get_model


class Command(BaseCommand):
    __doc__ = help = docstring("""
    Show or change information about a certain object.

    Supply two+ arguments: app_label.model_name object_pk...
    """)

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
            # Fake Admin site to get to be deleted objects.
            class AnonymousUser:
                is_staff = is_superuser = False

                def has_perm(self, perm):
                    return False

            # Hacks to force has_admin=False
            class AdminSite:
                name = 'irrelevant'
                _registry = {}

            using = 'default'
            retval = get_deleted_objects(
                (object,), object._meta,
                AnonymousUser(), AdminSite(), using)

            (dependent_objects, _, perms_needed, protected) = retval

            object._rdepends = dependent_objects
        return object._rdepends

    def print_rdepend_count(self, object):
        self.stdout.write(self.count_rdepends(object))

    def print_stat(self, object):
        dependent_count = self.count_rdepends(object)
        dependent_objects = self.get_rdepends(object)

        def prn(name, ilevel):
            self.stdout.write('      : %s- %s' % ('  ' * ilevel, name))

        def children_print(children, indent=0):
            for child in children:
                if isinstance(child, type([])):
                    children_print(child, indent + 1)
                else:
                    prn(child, indent)

        opts = object._meta
        if hasattr(opts, 'module_name'):  # renamed to model_name
            opts.model_name = opts.module_name

        identifier = '%s.%s:%s' % (opts.app_label, opts.model_name, object.pk)
        self.stdout.write('    ID: %s' % (identifier,))
        self.stdout.write(' Value: %s' % (object,))
        if hasattr(object, 'created'):
            self.stdout.write('Create: %s' % (object.created,))
        if hasattr(object, 'modified'):
            self.stdout.write('Modify: %s' % (object.modified,))
        if dependent_count:
            self.stdout.write('  Deps: %s ==>' % (dependent_count,))
            children_print(dependent_objects[1:])
        else:
            self.stdout.write('  Deps: %s' % (dependent_count,))
