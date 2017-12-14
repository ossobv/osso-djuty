# vim: set ts=8 sw=4 sts=4 et ai:
try:
    u = str
except NameError:
    u = str

from osso.sms import gsmencoding


__all__ = ('gsmencoding', 'sms_bodies_needed', 'sms_split')
gsmencoding  # touch for PEP


def sms_bodies_needed(number_of_bytes, single_sms_len=160, multi_sms_len=153):
    '''
    Count how many SMS bodies we need for this message.

    THIS FUNCTION IS DEPRECATED, SEE BUGS

    Assumptions:
    (1) We're using the GSM 03.38 7-bit alphabet.
    (2) In an SMS we can cram 140 octets (160 septets).
    (3) User data header (UDH) for SMS concatenation requires 6 octets,
        meaning that we lose 7 characters (ceil(6 bytes * 8 / 7)).

    Bugs:
    (1) We assume we're using the GSM 03.38 7-bit alphabet. There are
        other encodings (e.g. UTF-16).
    (2) The GSM 03.38 7-bit alphabet has a couple of 14 bit characters
        (the extended set), including [, ], {, }, EUR. This function has
        no way of knowing whether they are present. Note that sms_split
        takes care of this deficiency.

    Simple tests:
    >>> from .utils import sms_bodies_needed
    >>> [sms_bodies_needed(i) for i in (0, 1, 159, 160, 161)]
    [0, 1, 1, 1, 2]
    >>> [sms_bodies_needed(i)
    ...  for i in (305, 306, 307, 308, 458, 459, 460, 461)]
    [2, 2, 3, 3, 3, 3, 4, 4]
    >>> sms_bodies_needed(120, single_sms_len=120, multi_sms_len=60)
    1
    >>> sms_bodies_needed(121, single_sms_len=120, multi_sms_len=60)
    3
    '''
    if number_of_bytes <= 0:
        return 0
    if number_of_bytes <= single_sms_len:
        return 1
    return (number_of_bytes + multi_sms_len - 1) // multi_sms_len


def sms_split(message, single_sms_len=160, multi_sms_len=153):
    '''
    Split a text message in multiple parts, preferably across word
    boundaries. The message input is expected as 7-bit ASCII or in
    unicode. The parts are returned as a list of unicode strings which
    may need to be encoded before sending them on.

    Like sms_bodies_needed we assume we'll be using the GSM 03.38 7-bit
    character set with 160 characters for one SMS or 153 per part for
    long SMS.

    If the number of septets exceeds the number of characters and the
    message won't fit, it removes as many escape sequences as needed
    (e.g. turning the 2-septet "[" into a 1-septet "<").

    >>> try:
    ...     u = unicode
    ... except NameError:
    ...     def strarr(arr):
    ...         assert all(isinstance(i, str) for i in arr)
    ...         return arr
    ... else:
    ...     def strarr(arr):
    ...         assert all(isinstance(i, unicode) for i in arr)
    ...         return [str(i) for i in arr]
    >>> from .utils import sms_split
    >>> strarr(sms_split(u'', single_sms_len=4, multi_sms_len=4))
    []
    >>> strarr(sms_split(u'abcde', single_sms_len=5, multi_sms_len=4))
    ['abcde']
    >>> strarr(sms_split(u'abc de', single_sms_len=5, multi_sms_len=4))
    ['abc ', 'de']
    >>> strarr(sms_split(u'ab c de', single_sms_len=5, multi_sms_len=4))
    ['ab c', ' de']
    >>> strarr(sms_split(u'a b c de', single_sms_len=5, multi_sms_len=4))
    ['a b ', 'c de']
    >>> strarr(sms_split(u'[]', single_sms_len=5, multi_sms_len=4))
    ['[]']
    >>> strarr(sms_split(u'[][]', single_sms_len=5, multi_sms_len=4))
    ['<><]']
    >>> strarr(sms_split(u'[][][]', single_sms_len=5, multi_sms_len=4))
    ['<><>', '[]']
    '''
    message = u(message)
    if len(message) == 0:
        return []

    if len(message) <= single_sms_len:
        expected_bodies = 1
        max_chars = single_sms_len
    else:
        expected_bodies = (len(message) + multi_sms_len - 1) // multi_sms_len
        max_chars = multi_sms_len * expected_bodies

    # Encode the message in the GSM charset so we can see the real size.
    message = message.encode('gsm-0338', 'replace')
    # If the bodies needed for len(message) exceeds that of count, we
    # must shorten the message.
    if len(message) > max_chars:
        # Urgh. This is a very very crude way of trimming
        # characters. Message can only have become larger in length
        # than max_chars if the encoded message contains escape
        # sequences for the extended characters (\x1b ..). The
        # escape sequences are designed such that removal of the ESC
        # leaves a similar character.
        message = message.replace(b'\x1b', b'', len(message) - max_chars)

    # If this is a single SMS, we're done.
    if expected_bodies == 1:
        assert len(message) <= 160
        return [message.decode('gsm-0338')]

    # Attempt to split it on the space character first and try if we can
    # fit that in expected_bodies. We could search backwards here so the
    # followup messages could start with a space, but getting a first
    # short message is highly confusing. (Hence we attempt to place the
    # space in the first message to maximize the fit.)
    ret = []
    message
    start = 0
    end = len(message) - multi_sms_len
    while start < end:
        # Search for the space (attempt to put it in the second message).
        pos = message.rfind(b' ', start + 1, start + multi_sms_len + 1)
        if pos == -1:
            pos = start + multi_sms_len
            # Okay, we might split this across an escape. F it. Beware
            # that you might get invalid GSM chars this way.
            ret.append(message[start:pos].decode('gsm-0338'))
        else:
            if pos < start + multi_sms_len:
                pos += 1  # this message ends with the space
            ret.append(message[start:pos].decode('gsm-0338'))
        start = pos
    ret.append(message[start:].decode('gsm-0338'))

    # Okay.. was this good enough?
    if len(ret) == expected_bodies:
        return ret

    # It wasn't. Split the message the old fashioned way.
    return [message[i:(i + multi_sms_len)].decode('gsm-0338')
            for i in range(0, len(message), multi_sms_len)]
