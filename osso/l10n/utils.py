# vim: set ts=8 sw=4 sts=4 et ai:


def _parse_int(value):
    #assert value
    for i, c in enumerate(value):
        if not c.isdigit():
            break
    else:
        i += 1
    return int(value[0:i]), i


def natcmp(a, b):
    """
    >>> x = ['a', 'b', 'Z1', '', 'z1', 'zubar', 'z0', 'z10', 'z9', 'z1',
    ...      'a12b45c', 'a12b7c']
    >>> x.sort(cmp=natcmp)
    >>> x
    ['', 'Z1', 'a', 'a12b7c', 'a12b45c', 'b', 'z0', 'z1', 'z1', 'z9',
     'z10', 'zubar']
    """
    if not bool(a) or not bool(b):
        # One or both not set, cmp does the rest.
        return cmp(a, b)

    if a[0].isdigit() ^ b[0].isdigit():
        # One is numeric, the other isn't. cmp does the rest.
        return cmp(a, b)

    if not a[0].isdigit():
        # They're not numeric.
        if a[0] != b[0]:
            # Unequal, let cmp do the rest.
            return cmp(a, b)

        # Equal? Resume with next.
        return natcmp(a[1:], b[1:])

    # Ok. They're both numeric, fetch values and compare.
    anum, askip = _parse_int(a)
    bnum, bskip = _parse_int(b)

    if anum == bnum:
        # Same? Continue after.
        return natcmp(a[askip:], b[bskip:])

    if anum < bnum:
        # Lower.
        return -1

    # Higher.
    return 1
