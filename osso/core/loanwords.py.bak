# vim: set ts=8 sw=4 sts=4 et ai:


__all__ = ('car', 'enum', 'group_by', 'xrange64')


def car(list):
    '''
    Return the head of a list or None if the list is empty.
    It does not modify the original list. Origin: LISP.

    >>> a = []
    >>> b = [1]
    >>> c = [2, 3]
    >>> d = (4,)
    >>> car(a) == None and car(b) == 1 and car(c) == 2 and car(d) == 4
    True
    >>> len(a) == 0 and len(b) == 1 and len(c) == 2 and len(d) == 1
    True
    '''
    try:
        return list[0]
    except IndexError:
        return None


class enum(set):
    '''
    Create a simple enumeration type. Specify a the item names as arguments
    to the constructor. Origin: C.

    >>> State = enum('ACTIVE', 'INACTIVE', 'PENDING')
    >>> x = State.ACTIVE
    >>> y = State.INACTIVE
    >>> x == y
    False
    >>> x == State.ACTIVE
    True
    >>> try: State.ENOATTR
    ... except AttributeError: pass
    ... else: assert False
    >>> repr(State).startswith('enum(') and "'ACTIVE'" in repr(State)
    True
    >>> "'INACTIVE'" in repr(State) and "'PENDING'" in repr(State)
    True
    '''
    def __init__(self, *args):
        super(enum, self).__init__(args)

    def __getattr__(self, name):
        if name in self:
            return name
        raise AttributeError

    def __repr__(self):
        return '%s(%s)' % (self.__class__.__name__, ', '.join(map(repr, self)))


def group_by(keys, list_of_dictionaries):
    '''
    Takes a list of dictionaries and returns a dictionary of
    dictionaries with lists of values that were not used as keys.

    >>> from pprint import pprint as NORMALIZE_WHITESPACE

    >>> p = [{'price': 25, 'id': 1}, {'price': 5, 'id': 2},
    ...      {'price': 5, 'id': 3}]
    >>> group_by(('price',), p)
    {25: {'id': [1]}, 5: {'id': [2, 3]}}
    >>> group_by(('id',), p)
    {1: {'price': [25]}, 2: {'price': [5]}, 3: {'price': [5]}}

    >>> p = [
    ...     {'price': 25, 'currency': 'EUR', 'id': 1},
    ...     {'price': 5, 'currency': 'EUR', 'id': 2},
    ...     {'price': 5, 'currency': 'USD', 'id': 3},
    ...     {'price': 5, 'currency': 'USD', 'id': 4},
    ... ]
    >>> NORMALIZE_WHITESPACE(group_by(('price',), p))
    ... # doctest: +NORMALIZE_WHITESPACE
    {5: {'currency': ['EUR', 'USD', 'USD'], 'id': [2, 3, 4]},
     25: {'currency': ['EUR'], 'id': [1]}}
    >>> NORMALIZE_WHITESPACE(group_by(('price', 'currency'), p))
    ... # doctest: +NORMALIZE_WHITESPACE
    {(5, 'EUR'): {'id': [2]}, (5, 'USD'): {'id': [3, 4]},
     (25, 'EUR'): {'id': [1]}}
    '''
    output = {}
    for i in list_of_dictionaries:
        # Single key or multi-key?
        if len(keys) == 1:
            key = i[keys[0]]
        else:
            key = tuple(i[k] for k in keys)

        # Did we have one of these already?
        if key not in output:
            output[key] = {}
        inner = output[key]

        # Add all, except the keys
        for k, v in i.items():
            if k not in keys:
                if k not in inner:
                    inner[k] = []
                inner[k].append(v)
    return output


# CPython implementation detail: xrange() is intended to be simple and
# fast. Implementations may impose restrictions to achieve this. The C
# implementation of Python restricts all arguments to native C longs
# ("short" Python integers), and also requires that the number of
# elements fit in a native C long.
try:
    # Python2:
    # xrange(0xffffffffL, 0x100000002L)
    # Python1+2+3:
    if 0xffffffff == -1:  # 32-bits
        raise OverflowError()
except OverflowError:
    def xrange64(*args):
        '''
        An xrange replacement that works on 64 bits longs on 32-bits
        architectures.
        '''
        if len(args) == 1:
            start, stop, step = 0, args[0], 1
        elif len(args) == 2:
            start, stop, step = args[0], args[1], 1
        else:
            start, stop, step = args  # too few/many values to unpack on fail
        if step >= 0:
            while start < stop:
                yield start
                start += step
        else:
            while start > stop:
                yield start
                start += step
else:
    try:
        xrange64 = xrange
    except NameError:
        xrange64 = range  # python3
