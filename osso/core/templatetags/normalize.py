# vim: set ts=8 sw=4 sts=4 et ai:
#
# http://www.c-area.ch/code/django/templatetags/normalize.py
import re
from django.template import Node, Template, Library

register = Library()

class NormalizedNode(Node):
    def __init__(self, nodelist, patterns):
        self.nodelist = nodelist
        self.patterns = patterns

    def render(self, context):
        rendered = self.nodelist.render(context)
        for regexp, replacement in self.patterns:
            rendered = regexp.sub(replacement, rendered)
        return rendered

_patterns = {
    'all': (re.compile(r'\s+'), ''), # remove all whitespace
    'whitespace': (re.compile(r'\s+'), ' '), # replace all whitespace with a single space
    'linebreaks': (re.compile(r'\n{2,}'), '\n\n'), # replace multiple linebreaks with a single one
    'tabs': (re.compile(r'\t+'), '\t'), # replace multiple tabs with a single one
    'spaces': (re.compile(r' +'), ' '), # replace multiple spaces with a single one
    'emptylines': (re.compile(r'^\s*(\n|$)', re.MULTILINE), ''), # remove lines containing only whitespace as well as empty lines
    'strip': (re.compile(r'^[ \t\r\f\v]*(.*?)[ \t\r\f\v]*$', re.MULTILINE | re.DOTALL), r'\1'), # strip whitespace from the start and end of line
}

@register.tag(name="normalize")
def do_normalize(parser, token):
    """
    Normalize whitespace.

    Syntax::

        {% normalize [arg1, arg2, ...] %}
        ...
        {% endnormalize %}

    Possible arguments are:

        ==========================  ================================================
        Argument                    Description
        ==========================  ================================================
        ``all``                     Remove all whitespace
        ``emptylines``              Remove lines that are empty or contain only whitespace
        ``linebreaks``              Replace multiple linebreaks with a single one
        ``spaces``                  Replace multiple spaces with a single one
        ``tabs``                    Replace multiple tabs with a single one
        ``whitespace``              Replace all whitespace with a single space
        ==========================  ================================================

    If no arguments are given the default is 'whitespace'.

    Example usage::

        {% normalize emptylines tabs %}

        <ul>

                <li>bli</li>

                    <li>blu</li>

            <li>bla</li>
                <li>blo</li>

        </ul>

        {% endnormalize %}

    This example would return this HTML::

        <ul>
            <li>bli</li>
            <li>blu</li>
            <li>bla</li>
            <li>blo</li>
        </ul>

    Note that this template tag was mainly written for generating output where whitespace
    matters, such as configuration files and emails.
    Be careful when using this with html templates.
    It operates on the string level and doesn't care about document structure,
    HTML tags and such.
    """
    bits = token.contents.split()
    patterns = []
    args = bits[1:]
    if len(args) == 0:
        # default to 'whitespace' if no args given
        args.append('whitespace')

    for arg in args:
        pattern = _patterns.get(arg, None)
        if pattern:
            patterns.append(pattern)
        if arg == 'all' or arg == 'whitespace':
            break

    nodelist = parser.parse(('endnormalize',))
    parser.delete_first_token()
    return NormalizedNode(nodelist, patterns)
