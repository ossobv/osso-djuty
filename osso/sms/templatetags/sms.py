# vim: set ts=8 sw=4 sts=4 et ai:
from django import template
from django.utils.html import escape
from django.utils.safestring import mark_safe


register = template.Library()


@register.filter
# replace WORD JOINER (u2060) with a bit of html
# if highlight is non-zero it is the 1-based part of the SMS that needs
# highlighting
def visualize_sms_concatenation(value, highlight=None):
    # In some cases, we expect the data to be pre-escaped already. This
    # is flawed, but allows us to quickly upgrade the message data to
    # html.
    if '&lt;' in value or '&gt;' in value or '&amp;' in value or '/>' in value or '</' in value:
        esc = lambda i: i
    else:
        esc = escape

    if not highlight:
        return mark_safe(esc(unicode(value)).replace(u'\u2060', u'<span class="word-joiner">&#xb7;</span>'))

    items = unicode(value).split(u'\u2060')
    ret = []
    for i, item in enumerate(items):
        if i + 1 == highlight:
            ret.append('<span class="relevant">%s</span>' % (esc(item),))
        else:
            ret.append(esc(item))

    return mark_safe(u'<span class="word-joiner">&#xb7;</span>'.join(ret))
