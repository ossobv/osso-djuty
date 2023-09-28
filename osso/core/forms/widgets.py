# vim: set ts=8 sw=4 sts=4 et ai:
from itertools import chain
from django.forms import Select
from django.utils.html import conditional_escape
from django.forms.widgets import CheckboxInput, CheckboxSelectMultiple
try:
    from django.utils.encoding import force_text
except ImportError:
    from django.utils.encoding import force_unicode as force_text
from django.utils.safestring import mark_safe


def new_widget_with_attributes(widget_super, extra_attrs):
    '''
    Widget class generator function. Takes a widget to subclass and extra
    attributes to add to the widget.

    Want a read-only TextInput?

        ReadOnlyTextInput = new_widget_with_attributes(
            TextInput, {'readonly': 'readonly'})
    '''
    class _WidgetWithAttributes(widget_super):
        def render(self, name, value, attrs=None, renderer=None):
            if attrs is None:
                attrs = {}
            attrs.update(extra_attrs)
            return super().render(name, value, attrs, renderer)
    return _WidgetWithAttributes


class CheckboxSelectMultipleWithJS(CheckboxSelectMultiple):
    def render(self, name, value, attrs=None, choices=(), renderer=None):
        '''
        This render function is copied from django/forms/widgets.py...
        ...and altered several times.
        '''
        attrs = attrs or {}
        if value is None:
            value = []
        has_id = attrs and 'id' in attrs
        final_attrs = self.build_attrs(attrs)
        output = []
        # Normalize to strings
        str_values = set([force_text(v) for v in value])
        for i, (option_value, option_label) in enumerate(chain(self.choices,
                                                               choices)):
            # If an ID attribute was given, add a numeric index as a suffix,
            # so that the checkboxes don't all have the same ID attribute.
            if has_id:
                final_attrs = dict(final_attrs, id='%s_%s' %
                                   (attrs['id'], i), style='display:inline;')
                label_for = ' for="%s"' % final_attrs['id']
            else:
                label_for = ''

            cb = CheckboxInput(final_attrs,
                               check_test=(lambda value: value in str_values))
            option_value = force_text(option_value)
            rendered_cb = cb.render(name, option_value, renderer=renderer)
            option_label = conditional_escape(force_text(option_label))
            output.append('<label%s style="display:block;">%s %s</label>' %
                          (label_for, rendered_cb, option_label))

        # Optionally wrap it in spans
        COLUMNS, MINVALUES = 3, 8
        if len(output) > MINVALUES:
            per_column = int(float(len(output) + COLUMNS - 1) / COLUMNS)
            for i in reversed(list(range(
                    per_column, len(output), per_column))):
                output.insert(i, ('</span><span class="column"'
                                  ' style="display:block;">'))
            output.insert(0, ('<span class="large-multiple-choice">'
                              '<span class="column" style="display:block;">'))
            output.append('</span><br style="clear:both;"/></span>')
        else:
            # Always add the large-multiple-choice classes.. otherwise the
            # layout will mismatch.
            output.insert(0, ('<span class="large-multiple-choice">'
                              '<span class="column" style="display:block;">'))
            output.append('</span><br style="clear:both;"/></span>')

        # Code below is from old checkboxselectmultiplewithjs
        buttons = ' / '.join(
            ('''<a href="#" onclick="var checkboxes=document.'''
             '''getElementsByName('%s');'''
             '''for(var i=0;i&lt;checkboxes.length;i++){'''
             '''checkboxes[i].checked=%s;}return false;">%s</a>''') %
            (i[0], i[1], i[2])
            for i in ((name, 'true', 'Select All'), (name, 'false', 'None'))
        )
        output = ('<span class="large-multiple-choice-quickselect">' +
                  buttons + '</span><br/>' + '\n'.join(output))
        return mark_safe(output)


# class CheckboxSelectMultipleWithJS(CheckboxSelectMultiple):
#     def render(self, name, value, attrs=None, choices=(), renderer=None):
#         def get_js(selection_status):
#             return '''
#         var checkboxes = document.getElementsByName('%s');
#         for (var i = 0; i < checkboxes.length; i++) {
#             checkboxes[i].checked = %s;
#         }''' % (name, selection_status)
#
#         script = '''
#         <a href="#" onclick="%s; return false;">Select All</a> /
#         <a href="#" onclick="%s; return false;">None</a>
#         ''' % (get_js('true'), get_js('false'))
#
#         widget_html = (super(CheckboxSelectMultipleWithJS, self)
#                        .render(name, value, attrs, choices))
#         return mark_safe(script+widget_html)


class EditableSelectWidget(Select):
    '''
    Widget to render a selectbox and a textfield of which either one may
    be chosen.
    '''
    def render(self, name, value, attrs=None, choices=(), renderer=None):
        # FIXME: the following three items
        # - check whether value is in queryset or choices and select the
        #   appropriate radio select
        # - fix the clean method of the Form field to allow new values as
        #   well
        # - ensure that the selectbox works if there are no values at all
        attrs['onchange'] = ('document.getElementById("%s__select")'
                             '.checked=true;') % attrs['id']
        return mark_safe(
            ('<span>'
             '<input style="float:left;" type="radio" name="%(id)s__type"'
             ' value="select" id="%(id)s__select" checked="checked"/>'
             '%(select)s'
             '<br style="clear:both;">'
             '<input style="float:left;" type="radio"'
             ' name="%(id)s__type" value="text" id="%(id)s__text"/>'
             '<input type="text" maxlength="%(max_length)s"'
             ' name="%(id)s__value" onchange="%(onchange)s"/>'
             '</span>') %
            {'id': attrs['id'],
             'select': (super(EditableSelectWidget, self)
                        .render(name, value, attrs, choices)),
             'max_length': self.max_length,
             'onchange': ('document.getElementById(&quot;%s__text&quot;)'
                          '.checked=true;' % attrs['id'])}
        )
