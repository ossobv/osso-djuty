# vim: set ts=8 sw=4 sts=4 et ai:
'''
Python Character Mapping Codec for GSM_03.38 and 7-bit packing methods.

Copyright (C) Walter Doekes 2010. License: GPLv3. Version: 1.0.

BUGS

- Decoding does not take the Greek glyph character similarity into
  account. This means that the A will always decode as 0x41 and never as
  0x0391.
'''
try:
    unicode
except NameError:
    def bchr(i):
        return bytes([i])
    bord = lambda x: x  # taking an element of bstr returns integer
else:
    bchr = chr
    bord = ord


import codecs

__all__ = ('pack7', 'unpack7', 'encode', 'decode')


# == Codec APIs ==

def pack7(input, left_pad=0):
    '''
    Pack a 7-bit string into 8-bits according to the GSM bit-packing
    algorithm. Optionally supply an amount of bits to pad on the left
    side.

    This bit-padding can come in useful when you need to 7-bit align
    a message. E.g. for a 6 byte UDH, you need to pad the remaining
    153 characters with 1 bit to a 134 byte rest-of-message.

    >>> from . import gsmencoding
    >>> assert gsmencoding.pack7(b'A!AaBbCc') == b'\\xc1P0,\\x14\\x0f\\xc7'
    '''
    shift, ret, i, j = 0, [], 0, len(input)
    input += b'\x00'  # add padding byte
    if 1 <= left_pad <= 6:
        input = b'\x00' + input
        shift = 7 - left_pad
        j += 1
    while i < j:
        ret.append((bord(input[i]) >> shift) |
                   ((bord(input[i + 1]) << (7 - shift)) & 0xff))
        i += 1 + bool(shift == 6)
        shift = (shift + 1) % 7
    return b''.join(bchr(i) for i in ret)


def unpack7(input):
    '''
    Unpack an 8-bit binary string into 7-bit characters according to
    the GSM bit-packing algorithm.

    >>> from . import gsmencoding
    >>> assert gsmencoding.unpack7(b'\\xc1P0,\\x14\\x0f\\xc7') == b'A!AaBbCc'
    '''
    shift, left, ret = 0, 0, []
    for i in input:
        num = bord(i)
        ret.append(((num << shift) & 0x7f) | left)
        left = num >> (7 - shift)
        if shift == 6:
            ret.append(left)
            left = 0
        shift = (shift + 1) % 7
    return b''.join(bchr(i) for i in ret)


def encode(input, errors='strict'):
    '''
    Encode the unicode input to the GSM 03.38 character set.
    '''
    ret = []
    for i, c in enumerate(input):
        try:
            ret.append(encoding_table[bord(c)])
        except KeyError:
            if errors == 'replace':
                ret.append(replacement_table.get(c, b'?'))
            else:
                raise UnicodeEncodeError('gsm-0338', input, i, i + 1,
                                         'not in character set')
    if len(input) and c == '@':
        ret.append(b'\x0d')  # otherwise the 0x00 would be treated as padding
    return b''.join(ret), len(input)


def decode(input, errors='strict'):
    '''
    Decode the GSM 03.38 character string.
    '''
    ret, i, j = [], 0, len(input)
    while i < j:
        num = bord(input[i])
        if num == 0x1b:
            new = decoding_extensions.get(input[i:(i + 2)])
            if new is None:
                ret.append(b'\x0a')
            else:
                ret.append(new)
                i += 1
        else:
            try:
                ret.append(decoding_table[num])
            except IndexError:
                raise UnicodeDecodeError('gsm-0338', input, i, i + 1,
                                         'ordinal not in range(128)')
        i += 1
    return u''.join(ret), j


# == Encodings module API ==

def getregentry(name):
    if name in 'gsm-0338':
        return codecs.CodecInfo(name='gsm-0338', encode=encode, decode=decode)
    return None

# == Decoding/Encoding Map ==

decoding_table = [i for i in (
    u'@\xa3$\xa5\xe8\xe9\xf9\xec\xf2\xe7\n\xd8\xf8\r\xc5\xe5'
    u'\u0394_\u03a6\u0393\u039b\u03a9\u03a0\u03a8\u03a3\u0398\u039e\xa0'
    u'\xc6\xe6\xdf\xc9'
    u' !"#\xa4%&\'()*+,-./'
    u'0123456789:;<=>?'
    u'\xa1ABCDEFGHIJKLMNOPQRSTUVWXYZ\xc4\xd6\xd1\xdc\xa7'
    u'\xbfabcdefghijklmnopqrstuvwxyz\xe4\xf6\xf1\xfc\xe0'
)]

decoding_extensions = {
    b'\x1b\x0a': u'\f',
    b'\x1b\x14': u'^',
    b'\x1b\x28': u'{',
    b'\x1b\x29': u'}',
    b'\x1b\x2f': u'\\',
    b'\x1b\x3c': u'[',
    b'\x1b\x3d': u'~',
    b'\x1b\x3e': u']',
    b'\x1b\x40': u'|',
    b'\x1b\x65': u'\u20ac',
}

encoding_table = dict((bord(c), bchr(i))
                      for i, c in enumerate(decoding_table))
encoding_table.update(dict((bord(c), i)
                           for i, c in decoding_extensions.items()))

replacement_table = {
    u'\t': b' ',
    u'`': b'\'',
    u'\xa2': b'c',
    u'\xa6': b'|',
    u'\xa8': b'"',
    u'\xa9': b'c',
    u'\xaa': b'a',
    u'\xab': b'<',
    u'\xae': b'r',
    u'\xb5': b'u',
    u'\xb6': b'P',
    u'\xb7': b'\'',
    u'\xbb': b'>',
    u'\xc0': b'A',
    u'\xc1': b'A',
    u'\xc2': b'A',
    u'\xc3': b'A',
    u'\xc7': b'C',
    u'\xc8': b'E',
    u'\xca': b'E',
    u'\xcb': b'E',
    u'\xcc': b'I',
    u'\xcd': b'I',
    u'\xce': b'I',
    u'\xcf': b'I',
    u'\xd0': b'D',
    u'\xd2': b'O',
    u'\xd3': b'O',
    u'\xd4': b'O',
    u'\xd5': b'O',
    u'\xd7': b'x',
    u'\xd9': b'U',
    u'\xda': b'U',
    u'\xdb': b'U',
    u'\xdd': b'Y',
    u'\xde': b'b',
    u'\xe1': b'a',
    u'\xe2': b'a',
    u'\xe3': b'a',
    u'\xea': b'e',
    u'\xeb': b'e',
    u'\xed': b'i',
    u'\xee': b'i',
    u'\xef': b'i',
    u'\xf0': b'd',
    u'\xf3': b'o',
    u'\xf4': b'o',
    u'\xf5': b'o',
    u'\xf7': b'/',
    u'\xfa': b'u',
    u'\xfb': b'u',
    u'\xfd': b'y',
    u'\xfe': b'b',
    u'\xff': b'y',
}

# == Register codec ==

codecs.register(getregentry)

# == Examples ==

if __name__ == '__main__':
    assert pack7(b'A!AaBbCc') == b'\xc1P0,\x14\x0f\xc7'
    assert unpack7(b'\xc1P0,\x14\x0f\xc7') == b'A!AaBbCc'
    x = 'abc[]@\xe5'.encode('gsm-0338')
    print(repr(x))
    x = x.decode('gsm-0338')
    print(repr(x))
    # E8 32 9B FD 06 DD DF 72 36 19
    print(' '.join('%02X' % bord(i) for i in pack7(b'hello world')))
    # D0 65 36 FB 0D BA BF E5 6C 32
    print(' '.join('%02X' % bord(i) for i in pack7(b'hello world', 1)))
