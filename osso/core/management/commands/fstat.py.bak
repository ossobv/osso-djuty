# vim: set ts=8 sw=4 sts=4 et ai:
from django.core.exceptions import ObjectDoesNotExist
from django.db import models
from osso.core.management.base import BaseCommand, CommandError, docstring


class Command(BaseCommand):
    __doc__ = help = docstring("""
    Show information about FileFields and the filesystem availability.

    Supply one or two arguments:
        app_label.model_name.field_name
        [skip_upto_and_including_pk]
    """)

    def handle(self, *args, **kwargs):
        try:
            app_model_field = ''.join(args[0:1])
            app_label, model_name, field_name = app_model_field.split('.')
        except ValueError:
            raise CommandError('The app_label.model_name.field_name argument '
                               'looks wrong: %r' % (app_model_field,))

        try:
            model = models.get_model(app_label, model_name)
        except ObjectDoesNotExist:
            raise CommandError('No model found for app_label %s with '
                               'model_name %s' % (app_label, model_name))

        # Cannot use "hasattr(model, field_name)" here, because it
        # raises an AttributeError because you should only access it
        # on an instance, not on the class.
        if field_name not in dir(model):
            raise CommandError('Field %r not found on model %s' %
                               (field_name, model.__name__))

        if len(args) == 1:
            pk_skip = None
        elif len(args) == 2:
            pk_skip = args[1]
        else:
            raise CommandError('Got unexpected arguments: %r' % (args[2:],))

        self.check_files(model, field_name, pk_skip)

    def check_files(self, model, field_name, pk_skip):
        def escape(value):
            value = unicode(value).encode('utf-8')
            value = (value
                     .replace('\\', '\\\\')
                     .replace('\t', '\\t')
                     .replace('\r', '\\r')
                     .replace('\n', '\\n'))
            value = ''.join((i, '\\x%02x' % ord(i))[ord(i) < 0x20]
                            for i in value)
            return value

        qs = model.objects.order_by('pk')
        if pk_skip is not None:
            qs = qs.filter(pk__gt=pk_skip)

        for object_ in qs.iterator():
            field = getattr(object_, field_name)
            if field:
                filename = escape(field.path)
                try:
                    field.open()
                except:
                    status = 'FAIL'
                else:
                    status = 'OK'
                    field.close()
            else:
                status = 'OK'
                filename = '-'
            print('%s\t%s\t%s' % (escape(object_.pk), status, filename))
