from django.forms.forms import BoundField


class FieldsetBoundField(BoundField):
    def __init__(self, form, field, name, fieldset):
        super(FieldsetBoundField, self).__init__(form, field, name)
        self.fieldset = fieldset


class Fieldset(object):
    '''
    Fieldset represents a html fieldset with a ``name``, ``description``
    and css ``classes``.
    '''
    def __init__(self, form, name='', description='', fields=(), classes=()):
        self.form = form
        self.name = name
        self.description = description
        self.fields = fields
        self.classes = u' '.join(classes)

    def hidden_fields(self):
        """
        Returns a list of all the BoundField objects that are hidden fields.
        Useful for manual form layout in templates.
        """
        return [field for field in self if field.is_hidden]

    def visible_fields(self):
        """
        Returns a list of BoundField objects that aren't hidden fields.
        The opposite of the hidden_fields() method.
        """
        return [field for field in self if not field.is_hidden]

    def __iter__(self):
        form = self.form
        form_fields = form.fields
        for name in self.fields:
            try:
                field = form_fields[name]
            except KeyError:  # field was removed from the form instance
                continue
            yield FieldsetBoundField(form, field, name, self)


def process_fieldsets_meta(form):
    '''
    Process the fieldset Meta class attrribute into a list of fieldsets.
    '''
    if not hasattr(form, 'Meta') or not hasattr(form.Meta, 'fieldsets'):
        return [Fieldset(form=form, fields=form.fields.keys())]
    return [Fieldset(form=form, name=name, **options) for name, options in form.Meta.fieldsets]


class FieldsetMixin(object):
    '''
    FieldsetMixin allows the definition of fieldsets on the
    forms Meta class. The template can iterate over the fields
    and get the fieldset it belongs to or can iterate over the
    fieldsets and the fields that belong to it.
    '''
    def __init__(self, *args, **kwargs):
        super(FieldsetMixin, self).__init__(*args, **kwargs)
        self.fieldsets = process_fieldsets_meta(self)

    def __iter__(self):
        form_fields = self.fields
        for fieldset in self.fieldsets:
            for name in fieldset.fields:
                try:
                    field = form_fields[name]
                except KeyError:  # field was removed from the form instance
                    continue
                yield FieldsetBoundField(self, field, name, fieldset)
