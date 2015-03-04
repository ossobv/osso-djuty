# vim: set ts=8 sw=4 sts=4 et ai:
import re
from django import forms
from django.forms.models import ModelChoiceIterator
from django.utils.translation import ugettext_lazy as _
from osso.core.forms.widgets import (new_widget_with_attributes,
                                     EditableSelectWidget)
from osso.core.types import cidr4


safecharfield_re = re.compile('[\x00-\x08\x0a-\x1f]')
safetextfield_re = re.compile('[\x00-\x08\x0b-\x1f]')


class SafeCharField(forms.CharField):
    def clean(self, value):
        value = super(SafeCharField, self).clean(value)
        return safecharfield_re.sub('', value)


class Cidr4Field(forms.CharField):
    default_error_messages = {
        'invalid': _('An IPv4 address in CIDR notation must be a.b.c.d/e.'),
    }

    def __init__(self, *args, **kwargs):
        kwargs['max_length'] = 32  # max is 18, but allow some blanks
        super(Cidr4Field, self).__init__(*args, **kwargs)

    def clean(self, value):
        value = super(Cidr4Field, self).clean(value)
        if value == '' and not self.required:
            return None
        try:
            value = cidr4(value)
        except ValueError:
            raise forms.ValidationError(self.default_error_messages['invalid'])
        return value


class EditableSelectIterator(ModelChoiceIterator):
    def choice(self, obj):
        value = getattr(obj, self.field.to_field_name)
        return value, value


class EditableSelectField(forms.ModelChoiceField):
    widget = EditableSelectWidget

    def __init__(self, *args, **kwargs):
        kwargs['empty_label'] = None
        self.widget.max_length = kwargs.pop('max_length')
        super(EditableSelectField, self).__init__(*args, **kwargs)

    def _get_choices(self):
        if hasattr(self, '_choices'):
            return self._choices
        return EditableSelectIterator(self)

    choices = property(_get_choices, forms.ChoiceField._set_choices)


class FormatterCharField(forms.CharField):
    class _WithAttributes(object):
        def __getattr__(self, name):
            return self.__class__()

        def __str__(self):
            return 'whatever'
        __repr__ = __unicode__ = __str__

    CLEAN_VALUE_DEFAULT = 'whatever'
    CLEAN_VALUE_WITH_ATTRIBUTES = _WithAttributes()

    default_error_messages = {
        'formaterror': _(
            'Unmatched brace or illegal format string specifiers. '
            'Use {field} as replacement needle and {{ and }} for '
            'literal braces.'),
        'keyerror': _(
            'Invalid format field found. Please use one or more of %s.'),
        'attributeerror': _(
            'Invalid format field found. Indexes/properties of fields are '
            'not allowed.'),
    }

    def __init__(self, *args, **kwargs):
        """
        format_fields==('somevalue', 'othervalue')

        If accept_newlines==True, then we do not strip linefeeds from the
        input.

        If you want to allow attribute indexing ("foo {foo.bar} baz")
        you'll need to pass a clean_value==X that allows such an
        attribute.

        For example:

            class AnyProperty(object):
                def __getattr__(self, name):
                    return self.__class__()
                def __str__(self):
                    return 'whatever'
                __repr__ = __unicode__ = __str__

        For your convenience, an object of that class is attached to
        this class, so you can do this:

            FormatterCharField(
                format_fields=('foo',),
                clean_value=FormatterCharField.CLEAN_VALUE_WITH_ATTRIBUTES)
        """
        clean_value = kwargs.pop('clean_value',
                                 FormatterCharField.CLEAN_VALUE_DEFAULT)
        self.format_dict = dict((i, clean_value)
                                for i in kwargs.pop('format_fields', ()))
        self.accept_newlines = kwargs.pop('accept_newlines')

        super(FormatterCharField, self).__init__(*args, **kwargs)

    def clean(self, value):
        value = super(FormatterCharField, self).clean(value)
        if self.accept_newlines:
            value = safetextfield_re.sub('', value)
        else:
            value = safecharfield_re.sub('', value)
        try:
            # Check the validity
            value.format(**self.format_dict)
        except ValueError:
            msg = self.default_error_messages['formaterror']
            raise forms.ValidationError(msg)
        except (IndexError, KeyError):
            msg = self.default_error_messages['keyerror']
            raise forms.ValidationError(
                msg % (', '.join('{%s}' % i for i in self.format_dict),))
        except (AttributeError, TypeError):
            msg = self.default_error_messages['attributeerror']
            raise forms.ValidationError(msg)
        return value


class PhoneNumberField(forms.CharField):
    widget = new_widget_with_attributes(
        forms.TextInput,
        {'onchange': 'this.value=this.value.replace(/[^0-9+]/g,"");'})
    default_error_messages = {
        'invalid': _('A valid phone number must begin with either a region '
                     'code (0xx) or an international prefix (00xx or +xx).'),
    }

    def __init__(self, *args, **kwargs):
        # TODO:wjd:2013-12-10: make the +31 intprefix default changeable
        self.intprefix = kwargs.pop('intprefix', '31')
        kwargs['max_length'] = kwargs.pop('max_digits', 32)
        kwargs.pop('decimal_places', None)
        super(PhoneNumberField, self).__init__(*args, **kwargs)

    def clean(self, value):
        value = super(PhoneNumberField, self).clean(value)
        if value == '' and not self.required:
            return None
        value = value.strip()

        if value[0] == '+':
            value = value[1:]
        elif len(value) > 1 and value[0] == '0' and value[1] == '0':
            value = value[2:]
        elif len(value) > 1 and value[0] == '0' and value[1] in '123456789':
            value = '%s%s' % (self.intprefix, value[1:])
        else:
            raise forms.ValidationError(self.default_error_messages['invalid'])

        if value[0] == '0' or any(i not in '0123456789' for i in value):
            raise forms.ValidationError(self.default_error_messages['invalid'])

        return '+%s' % value
