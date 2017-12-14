# vim: set ts=8 sw=4 sts=4 et ai:
import unittest
from xml.dom.minidom import parseString


class ParseError(Exception):
    pass


def htmlesc(raw):
    return (raw.replace('&', '&amp;').replace('<', '&lt;')
            .replace('>', '&gt;').replace('"', '&#34;'))


def xmlescape(string, escape_also=''):
    """
    Escapes & < and > to &amp; &lt; and &gt; and converts any unicode
    character not in the ASCII range into an &#NN; escape.

    Optionally supply a list/string of characters to escape as well.
    E.g. when escaping element attribute values, you'll want to add the
    double and/or single quote.

    Don't do anything stupid like try to escape any of a..z 0..9
    & # ;
    """
    if isinstance(string, str):
        string = string.decode('utf-8')
    if not isinstance(string, str):
        raise TypeError("xmlescape() argument must be a string type, "
                        "not '%s'" % (type(string).__name__,))
    if not isinstance(escape_also, str):
        raise TypeError("xmlescape() optional argument escape_also "
                        "must be a binary string type")
    if any(i in 'abcdefghijklmnopqrstuvwxyz0123456789&#;'
           for i in escape_also):
        raise ValueError("xmlescape() will not handle your escape_also "
                         "arguments like you expect")

    safe = (str(string).replace('&', '&amp;').replace('<', '&lt;')
            .replace('>', '&gt;'))
    ascii = safe.encode('ascii', 'xmlcharrefreplace')
    for i in escape_also:
        ascii = ascii.replace(i, '&#%d;' % (ord(i),))
    return ascii


def xmlstrip(string):
    """
    Strip whitespace from nodes that do not contain text but *do*
    contain other nodes. Useful for storing XML blobs in a less verbose
    manner.
    """
    from lxml import etree  # should we use xml.dom instead?
    parser = etree.XMLParser(remove_blank_text=True)
    root = etree.fromstring(string, parser)
    return etree.tostring(root, pretty_print=False)


def string2dom(string):
    """
    Parse/convert a string into an opaque DOM.
    """
    return parseString(string)


def dom2dictlist(dom, inside=(), li=None, strict=True):
    """
    Take the opaque DOM, go into the tags specified by inside and
    collect the dictionary contents.

    Example input: <elems><el><a>1</a><b>2</b></el>
                          <el><a>3</a><b>4</b></el></elems>
                   (inside=('elems',))
    Example output: [{'a': 1, 'b': 2}, {'a': 3, 'b': 4}]

    If other elements than a list item can occur in <elems>, you must
    specify li.
    """
    # Dive into the DOM as long as there are elements in the 'inside'
    # list.
    if inside:
        for node in dom.childNodes:
            if (node.nodeType == node.ELEMENT_NODE and
                    node.tagName == inside[0]):
                return dom2dictlist(node, inside=inside[1:], li=li,
                                    strict=strict)
        raise ParseError('Element <%s/> not found in dom' % (inside[0],), dom)

    elem_name = li
    ret = []
    for node in dom.childNodes:
        if node.nodeType == node.ELEMENT_NODE:
            # We may not know what a list element looks like beforehand.
            if li and node.tagName != elem_name:
                # List element supplied and this is not one. Ignore.
                continue
            elif elem_name is not None and node.tagName != elem_name:
                # List element not supplied and this is not the same as
                # the last one. Abort.
                raise ParseError('Unexpected element <%s/> in dom, '
                                 'expected <%s/>' % (node.tagName, elem_name),
                                 dom)
            elif elem_name is None:
                # Store what the list element is.
                elem_name = node.tagName

            elem = {}
            for child_node in node.childNodes:
                if child_node.nodeType == child_node.ELEMENT_NODE:
                    key = child_node.tagName
                    value = child_node.childNodes
                    if len(value) == 0:
                        value = ''
                    elif (len(value) == 1 and
                            value[0].nodeType == child_node.TEXT_NODE):
                        value = value[0].nodeValue
                    else:
                        if strict:
                            raise ParseError('Unexpected node contents in '
                                             '<%s/>' % (key,),
                                             dom)
                        value = None
                    elem[key] = value
            ret.append(elem)
    return ret


class UtilsTest(unittest.TestCase):
    def test_test(self):
        self.assertEqual(1, 1)

    def test_dom2dictlist1(self):
        input = b'''<?xml version="1.0" encoding="UTF-8"?>
        <abc>
            <unused_and_skipped/>
            <def>
                <ghi>
                    <a>1</a>
                </ghi>
                <ghi>
                    <a>1</a><b>2</b>
                </ghi>
                <ghi>
                    <a>3</a><b>5</b>
                </ghi>
                <!-- throw in a bit of valid but odd-looking stuff -->
                <ghi/>
                <ghi><br/></ghi>
            </def>
            <def>
                <ghi><!-- this def will be skipped entirely --></ghi>
            </def>
        </abc>
        '''
        expected = [{'a': '1'}, {'a': '1', 'b': '2'},
                    {'a': '3', 'b': '5'}, {}, {'br': ''}]
        output = dom2dictlist(parseString(input), inside=('abc', 'def'))
        self.assertEqual(expected, output)

    def test_dom2dictlist2(self):
        input = (b'<?xml version="1.0" encoding="UTF-8"?>'
                 b'<banks><bank/></banks>')
        expected = [{}]
        output = dom2dictlist(parseString(input), inside=('banks',))
        self.assertEqual(expected, output)

    def test_dom2dictlist3(self):
        input = b'<?xml version="1.0" encoding="UTF-8"?><banks>   </banks>'
        expected = []
        output = dom2dictlist(parseString(input), inside=('banks',))
        self.assertEqual(expected, output)

    def test_dom2dictlist4(self):
        input = (b'<?xml version="1.0" encoding="UTF-8"?>'
                 b'<a><b><c><d/></c></b></a>')
        self.assertRaises(ParseError, dom2dictlist, parseString(input),
                          inside=())

    def test_dom2dictlist5a(self):
        input = (b'<?xml version="1.0" encoding="UTF-8"?>'
                 b'<a><b><c>1</c></b><b><d>2</d></b><b><e><f/></e></b></a>')
        self.assertRaises(ParseError, dom2dictlist, parseString(input),
                          inside=('a'), li='b')

    def test_dom2dictlist5b(self):
        input = (b'<?xml version="1.0" encoding="UTF-8"?>'
                 b'<a><b><c>1</c></b><b><d>2</d></b><b><e><f/></e></b></a>')
        expected = [{'c': '1'}, {'d': '2'}, {'e': None}]
        output = dom2dictlist(parseString(input), inside=('a'), li='b',
                              strict=False)
        self.assertEqual(expected, output)

    def test_xmlescape1(self):
        input = '<br/>'
        expected = '&lt;br/&gt;'
        self.assertEqual(expected, xmlescape(input))

    def test_xmlescape2(self):
        input = 'ABC&amp;"\u20ac'
        expected = 'ABC&amp;amp;"&#8364;'
        self.assertEqual(expected, xmlescape(input))

    def test_xmlescape3(self):
        input = 'ABC&amp;"'
        expected = 'ABC&amp;amp;&#34;'
        self.assertEqual(expected, xmlescape(input, escape_also='"'))

    def test_xmlescape4(self):
        self.assertEqual(xmlescape('123'), '123')
        self.assertEqual(xmlescape('abc'), 'abc')
        self.assertEqual(xmlescape('<&>'), '&lt;&amp;&gt;')
        self.assertEqual(xmlescape('<&>'), '&lt;&amp;&gt;')
        self.assertEqual(xmlescape('\xe2\x82\xac'), '&#8364;')
        self.assertEqual(xmlescape('\u20ac'), '&#8364;')
        self.assertEqual(xmlescape('1<2'), '1&lt;2')

    def test_xmlstrip1(self):
        input = '''<?xml version="1.0"?><response>
            <order>
                <transaction_id>dbe96a68fb47d8115c1b6a8c5d22d90e</transaction_id>
                <amount>995</amount>
                <currency>EUR</currency>
                <payed>false</payed>
                <message>This iDEAL-order wasn't payed for, or was already \
checked by you. (We give payed=true only once, for your protection)</message>
                <status>Cancelled</status>
            </order>
        </response>'''
        expected = ('<response><order><transaction_id>'
                    'dbe96a68fb47d8115c1b6a8c5d22d90e</transaction_id>'
                    '<amount>995</amount><currency>EUR</currency>'
                    '<payed>false</payed><message>'
                    "This iDEAL-order wasn't payed for, or was already "
                    "checked by you. "
                    '(We give payed=true only once, for your protection)'
                    '</message><status>Cancelled</status>'
                    '</order></response>')
        self.assertEqual(xmlstrip(input), expected)

    def test_xmlstrip2(self):
        input = ''' <a>  <b> ABC <def/> GHI </b> </a> '''
        expected = '''<a><b> ABC <def/> GHI </b></a>'''
        self.assertEqual(xmlstrip(input), expected)


if __name__ == '__main__':
    unittest.main()
