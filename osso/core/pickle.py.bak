# vim: set ts=8 sw=4 sts=4 et ai:
try:
    from cPickle import dumps, loads
except ImportError:
    from pickle import dumps, loads


__all__ = ('cescape', 'cunescape', 'dumpascii', 'loadascii')


CESCAPE_TABLE = dict(enumerate(
    ['\\x00', '\\x01', '\\x02', '\\x03', '\\x04', '\\x05', '\\x06', '\\a']
    + ['\\b', '\\t', '\\n', '\\v', '\\f', '\\r', '\\x0e', '\\x0f']
    + ['\\x%02x' % i for i in range(0x10, 0x20)]
    + [chr(i) for i in range(0x20, 0x80)]
    + ['\\x%02x' % i for i in range(0x80, 0x100)]
))
CESCAPE_TABLE[0x5c] = '\\\\'
assert len(CESCAPE_TABLE) == 256


def cescape(string):
    return ''.join([CESCAPE_TABLE[ord(i)] for i in str(string)])


def cunescape(string):
    string = str(string)
    pieces = []
    i = j = 0
    try:
        while True:
            i = string.index('\\', j)
            if i != j:
                pieces.append(string[j:i])
            if string[i + 1] == '\\':
                pieces.append('\\')
                j = i + 2
            elif string[i + 1] == 'x':
                pieces.append(chr(int(string[(i + 2):(i + 4)], 16)))
                j = i + 4
            elif string[i + 1] in 'abtnvfr':
                pieces.append(chr('abtnvfr'.index(string[i + 1]) + 7))
                j = i + 2
            else:
                assert False
    except (IndexError, ValueError):
        pieces.append(string[j:])
    return ''.join(pieces)


def dumpascii(data):
    # Waiting for http://code.djangoproject.com/ticket/2417
    # for now we use C-escapes to ensure it's CharField-safe
    return cescape(dumps(data))


def loadascii(data):
    # Waiting for http://code.djangoproject.com/ticket/2417
    # for now we use C-escapes to ensure it's CharField-safe
    return loads(cunescape(data))
