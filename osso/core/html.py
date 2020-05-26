# vim: set ts=8 sw=4 sts=4 et ai:
import re


__all__ = ('to_linear_text', 'to_pdf')


BLOCK_ELEMENTS = ('address', 'blockquote', 'center', 'dir', 'div', 'dl',
                  'fieldset', 'form', 'h1', 'h2', 'h3', 'h4', 'h5', 'h6',
                  'hr', 'isindex', 'menu', 'noframes', 'noscript', 'ol',
                  'p', 'pre', 'table', 'ul') + ('dd', 'dt', 'frameset',
                  'li', 'tbody', 'td', 'tfoot', 'th', 'thead', 'tr')
RE_WHITE = re.compile(r'\s+')
RE_WHITE_AROUND_LF = re.compile(r'\n +| +\n')
RE_DOUBLE_LF = re.compile(r'\n\n+')


def to_linear_text(html):
    '''
    >>> import os
    >>> fn = os.path.join(os.path.dirname(__file__), 'tests-data',
    ...                   'to_linear_text')
    >>> input = open(fn + '.html').read()
    >>> expected = open(fn + '.txt').read()
    >>> try:
    ...     result = to_linear_text(input)
    ... except ImportError:
    ...     pass
    ... else:
    ...     assert result == expected, ('Output dissimilar from %s.txt: %r' %
    ...                                 (fn, result))
    '''
    # Wow.. various imports break the doctests when placed at the top:
    # all tests in tests.py get reduced to 0 tests. (Observed with
    # different python versions, but 2.6.6 behaves even worse than
    # 2.7.{2,3}.)
    # Can't explain it, but we can safely move the imports here.
    try:
        from lxml.html import fromstring
    except ImportError as e:
        raise ImportError(e.args[0] + '\n\n*HINT* apt-get install python-lxml')
    from lxml.etree import Comment, ParserError

    def helper(parent):
        items = []
        for item in parent.getchildren():
            tag = item.tag
            # Is it a comment? Ignore
            if tag == Comment:
                continue
            # Is it a script or style block? Ignore
            if tag in ('script', 'style'):
                continue
            # Is it a block-level element? Add double whitespace
            is_block = tag in BLOCK_ELEMENTS
            if is_block:
                items.append('\n')
            elif tag == 'br':
                items.append('\n')
            # Does it contain text? Add it
            if item.text:
                items.append(RE_WHITE.sub(' ', item.text))
            # Does it have children? Add those
            items.extend(helper(item))
            # Add LF at end too
            if is_block:
                items.append('\n')
            # Do we have trailing text? Add that
            if item.tail:
                items.append(RE_WHITE.sub(' ', item.tail))
        return items

    # lxml.etree.ParserError: Document is empty
    if not html.strip():
        return ''

    try:
        doc = fromstring(html)
    except ValueError:
        # * "Unicode strings with encoding declaration are not supported."
        #   If we serve it an HTML document that begins with something like:
        #   '<?xml version="1.0" encoding="utf-8" ?>'
        #   The easy fix is to recode it to utf-8, but that only works if the
        #   declaration does in fact say utf-8... well... that should be the
        #   majority of cases.
        html = html.encode('utf-8')
        doc = fromstring(html)
    except ParserError as e:
        html = 'Parse error "%s" parsing this:\n\n%s' % (e, html)
        html = '<body><pre>%s</pre></body>' % (html.replace('&', '&amp')
                                                   .replace('<', '&lt;')
                                                   .replace('>', '&gt;'),)
        doc = fromstring(html)

    items = helper(doc)
    # Join part and remove space before and after LF and at start and end
    long_text = RE_WHITE_AROUND_LF.sub('\n', ''.join(items).strip())
    # Reduce multiple LFs to at most two
    long_text = RE_DOUBLE_LF.sub('\n\n', long_text)
    # Add trailing LF, unix likes this
    if long_text:
        long_text += '\n'
    return long_text


def to_pdf(html, destination=None):
    '''
    A wrapper around the ho.pisa CreatePDF stuff filtering the excess
    warnings.

    Destination can be a file or be left blank. The return value is a file-like
    object, positioned at the start.

    >>> try:
    ...     pdf = to_pdf('<html><body>cheesecake</body></html>')
    ... except ImportError:
    ...     hdr = '%PDF'
    ... else:
    ...     hdr = pdf.read(4)
    ...     pdf.close()
    >>> hdr
    '%PDF'
    '''
    # Load these from this function so it does not get triggered until
    # we need it.
    import warnings
    warnings.filterwarnings('ignore')  # silence the 'sets' deprecationwarning
    try:
        # from xhtml2pdf.pisa import CreatePDF
        # from xhtml2pdf.default import DEFAULT_CSS
        raise ImportError('Bah! xhtml2pdf does not handle tables (auto-width, '
                          'borders, backgrounds) correctly.')
        # Instead, you may do this:
        # > --- sx/pisa3/pisa_util.py.orig  2014-05-28 00:00:50.931100630 +0200
        # > +++ sx/pisa3/pisa_util.py       2014-05-28 00:01:23.283345829 +0200
        # > @@ -40,10 +40,11 @@ import shutil
        # >
        # >  rgb_re = re.compile("^.*?rgb[(]([0-9]+).*?([0-9]+).*?([0-9]+)[)].*?[ ]*$")
        # >
        # > -if not(reportlab.Version[0] == "2" and reportlab.Version[2] >= "1"):
        # > +_reportlab_version = tuple(map(int, reportlab.Version.split('.')))
        # > +if _reportlab_version < (2, 1):
        # >      raise ImportError("Reportlab Version 2.1+ is needed!")
        # >
        # > -REPORTLAB22 = (reportlab.Version[0] == "2" and reportlab.Version[2] >= "2")
        # > +REPORTLAB22 = _reportlab_version >= (2, 2)
        # >  # print "***", reportlab.Version, REPORTLAB22, reportlab.__file__
        # >
        # >  import logging
    except ImportError:
        try:
            from ho.pisa import CreatePDF
            from sx.pisa3.pisa_default import DEFAULT_CSS
        except ImportError as e:
            raise ImportError(e.args[0] + '\n\n*HINT* apt-get install '
                              'python-pisa (>= 3.0.12) or '
                              'xhtml2pdf (>= 0.0.6)')
    # We defer the loading of this because it somehow breaks the
    # doctests when placed at the top.
    try:
        from io import StringIO
    except ImportError:
        from io import StringIO

    if destination is None:
        destination = StringIO()
    else:
        destination.seek(0)

    html = html.encode('ascii', 'xmlcharrefreplace')
    source = StringIO(html)
    context = CreatePDF(src=source, dest=destination, default_css=DEFAULT_CSS)
    del context
    destination.seek(0)

    # CreatePDF also does extra importing that can raise warnings.
    import warnings
    warnings.filterwarnings('default')
    return destination
