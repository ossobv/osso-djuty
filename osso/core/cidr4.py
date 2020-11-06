# vim: set ts=8 sw=4 sts=4 et ai:
# We won't work on ancient (32-bit) systems where int!=long and 32 bits
# is the max integer.  Either use 64-bit or a newer python.  We need
# this check, because 0xffffffffL ('L') doesn't work anymore in
# python3.
from collections import namedtuple

if 0xffffffff == -1:
    raise NotImplementedError()


__all__ = ('cidr4',)


class _ComparableMixin(object):
    "Python3 does not do the __cmp__ method"
    def __lt__(self, other):
        return self.__cmp__(other) < 0

    def __le__(self, other):
        return self.__cmp__(other) <= 0

    def __eq__(self, other):
        return self.__cmp__(other) == 0

    def __ge__(self, other):
        return self.__cmp__(other) >= 0

    def __gt__(self, other):
        return self.__cmp__(other) > 0

    def __ne__(self, other):
        return self.__cmp__(other) != 0

    # Suppress py3 hash warning. Feel free to implement a hash method on
    # your subclass though.
    __hash__ = None


class cidr4(_ComparableMixin):
    """
    An IPv4 CIDR block (or individual IP in the case of a /32 netmask).

    >>> cidr4('1.2.3.4')
    cidr4("1.2.3.4")
    >>> str(cidr4('1.2.3.4/32'))
    '1.2.3.4'
    >>> cidr4('1.2.3.4/32').as_string()
    '1.2.3.4/32'
    >>> cidr4('1.2.3.4/32').as_string(ip_as_net=False)
    '1.2.3.4'
    >>> cidr4('1.2.3.4/30')
    cidr4("1.2.3.4/30")

    Test comparisons.

    >>> a, b = cidr4('1.64.255.128/32'), cidr4('1.64.255.128')
    >>> a == b and a <= b and a >= b
    True
    >>> b = cidr4('1.64.255.128/25') # larger subnet sorts earlier
    >>> b < a and b != a and not (b > a)
    True
    >>> c = cidr4('2.0.0.0/7')
    >>> c > b and c > a
    True

    Test initialization.

    >>> a = cidr4('1.64.255.128/32')
    >>> b = cidr4(a)
    >>> a == b
    True
    >>> try: cidr4('aap')
    ... except ValueError: pass
    ... else: assert False
    >>> try: cidr4('1.2.3.4/29') # .4 may have significant bits in (30, 31, 32)
    ... except ValueError: pass
    ... else: assert False
    >>> try: cidr4(None)
    ... except TypeError: pass
    ... else: assert False

    Test the new /255.255.255.0 notation.

    >>> a = cidr4('1.2.64.0/255.255.254.0')
    >>> str(a)
    '1.2.64.0/23'
    >>> a.as_verbose_string()
    '1.2.64.0/255.255.254.0'
    >>> a = cidr4('255.255.255.255/255.255.255.255')
    >>> a.as_verbose_string(ip_as_net=True)
    '255.255.255.255/255.255.255.255'
    >>> a.as_verbose_string(ip_as_net=False)
    '255.255.255.255'

    Test the in operator.

    >>> net = cidr4('192.168.1.0/24')
    >>> cidr4('192.168.1.0') in net
    True
    >>> cidr4('192.168.1.123') in net
    True
    >>> cidr4('192.168.1.64/26') in net
    True
    >>> cidr4('192.168.0.0/23') in net  # more low
    False
    >>> cidr4('192.168.0.0/16') in net  # more of everything
    False
    >>> cidr4('192.168.2.0/23') in cidr4('192.168.2.0/24')  # more high
    False
    >>> net in net
    True

    Test automatic casting and type errors on the in operator.

    >>> net = cidr4('192.168.1.0/24')
    >>> '1.2.3.4' in net
    False
    >>> '192.168.1.2/31' in net
    True
    >>> try: True in net
    ... except TypeError: pass
    ... else: assert False
    """
    __slots__ = ('address', 'sigbits')

    @classmethod
    def generate_cidr4_list_from_start_end(cls, start, end_ex):
        """
        Test generating a list from start to end, using the largst cidr
        blocks possible.

        >>> list(cidr4.generate_cidr4_list_from_start_end(
        ...     cidr4('1.2.3.70').address,
        ...     cidr4('1.2.3.81').address))
        [cidr4("1.2.3.70/31"), cidr4("1.2.3.72/29"), cidr4("1.2.3.80")]
        """
        assert start <= end_ex, (start, end_ex)
        while start < end_ex:
            freebits = 0
            addr = start
            while (addr & 1) == 0:
                freebits += 1
                addr >>= 1

            maxaddr = ((start >> freebits) + 1) << freebits
            if maxaddr <= end_ex:
                c = cidr4((start, 32 - freebits))
                start = maxaddr
            else:
                diff = end_ex - start
                diffbits = 0
                while diff > 0:
                    diffbits += 1
                    diff >>= 1
                c = cidr4((start, 32 - diffbits + 1))
                start = c.next().address

            yield c

    def __init__(self, value):
        if (isinstance(value, tuple) and len(value) == 2 and
                isinstance(value[0], int) and isinstance(value[1], int)):
            netmask = (0xffffffff << (32 - value[1])) & 0xffffffff
            if (value[0] & ~netmask) != 0:
                raise ValueError(
                    'Found non-zero bit to the right of the netmask.')
            self.address, self.sigbits = value
            return
        if isinstance(value, cidr4):
            self.address, self.sigbits = value.address, value.sigbits
            return
        if not isinstance(value, str):
            raise TypeError('Cannot convert %r to a cidr4 type' % (value,))

        value = str(value).strip()
        if '/' not in value:
            value += '/32'
        host, sigbits = value.split('/', 2)

        # 1.2.3.0/255.255.255.0 ?
        if '.' in sigbits:
            # may raise ValueError:
            a, b, c, d = [int(byte) for byte in sigbits.split('.', 4)]
            if (a < 0 or a > 255 or b < 0 or b > 255 or
                    c < 0 or c > 255 or d < 0 or d > 255):
                raise ValueError('Invalid netmask.')

            netmask = int(a) << 24 | int(b) << 16 | int(c) << 8 | int(d)
            # http://gurmeetsingh.wordpress.com/2008/08/05/fast-bit-counting-routines/
            tmp = (netmask -
                   ((netmask >> 1) & 0o33333333333) -
                   ((netmask >> 2) & 0o11111111111))
            sigbits = ((tmp + (tmp >> 3)) & 0o30707070707) % 63

            if netmask & ~(0xffffffff << (32 - sigbits)) != 0:
                raise ValueError('Invalid netmask.')
        # 1.2.3.0/24
        else:
            sigbits = int(sigbits)  # may raise ValueError

        # may raise ValueError:
        a, b, c, d = [int(byte) for byte in host.split('.', 4)]
        if (a < 0 or a > 255 or b < 0 or b > 255 or c < 0 or c > 255 or
                d < 0 or d > 255 or sigbits < 0 or sigbits > 32):
            raise ValueError('Not in CIDR4 notation.')
        address = int(a) << 24 | int(b) << 16 | int(c) << 8 | int(d)
        netmask = (0xffffffff << (32 - sigbits)) & 0xffffffff

        if (address & ~netmask) != 0:
            raise ValueError('Found non-zero bit to the right of the netmask.')

        self.address = address
        self.sigbits = sigbits

    def __cmp__(self, other):
        try:
            other = cidr4(other)
        except Exception:
            return NotImplemented
        try:
            return (cmp(self.address, other.address) or
                    cmp(self.sigbits, other.sigbits))
        except NameError:  # no cmp() in python3
            if self.address < other.address:
                return -1
            if self.address > other.address:
                return 1
            if self.sigbits < other.sigbits:
                return -1
            if self.sigbits > other.sigbits:
                return 1
            return 0

    def __setattr__(self, key, value):
        if key in self.__slots__ and not hasattr(self, key):
            super(cidr4, self).__setattr__(key, value)
        else:
            raise TypeError('immutable')

    def __repr__(self):
        return 'cidr4("%s")' % self.__str__()

    def __str__(self):
        return self.as_string(ip_as_net=False)

    def __contains__(self, subset):
        if not isinstance(subset, cidr4):
            subset = cidr4(subset)

        if self.sigbits > subset.sigbits:  # more bits is smaller
            return False
        netmask = (0xffffffff << (32 - self.sigbits)) & 0xffffffff
        return (subset.address & netmask) == self.address

    def next(self):
        return cidr4((
            self.address + (1 << (32 - self.sigbits)),
            self.sigbits))

    def truncated(self, sigbits):
        return cidr4((
            self.address & (0xffffffff << (32 - sigbits)),
            sigbits))

    def _as_ip(self, address):
        return '%d.%d.%d.%d' % (
            (address >> 24) & 0xff,
            (address >> 16) & 0xff,
            (address >> 8) & 0xff,
            (address) & 0xff)

    def as_from_to(self):
        first = self._as_ip(self.address)
        if self.sigbits == 32:
            return first
        return '[%s - %s]' % (first, self._as_ip(self.next().address - 1))

    def as_list(self):
        return [
            cidr4((i, 32)) for i in range(self.address, self.next().address)]

    def as_string(self, ip_as_net=True):
        return '%s%s' % (
            self._as_ip(self.address),
            ('', '/%d' % self.sigbits)[ip_as_net or self.sigbits != 32])

    def as_verbose_string(self, ip_as_net=True):
        if self.sigbits == 32 and not ip_as_net:
            return self.as_string(False)

        netmask = (0xffffffff << (32 - self.sigbits)) & 0xffffffff
        return '%s/%s' % (self._as_ip(self.address), self._as_ip(netmask))

    def __hash__(self):
        "You shouldn't mutate address/sigbits. If you do, this is wrong."
        return hash((self.address, self.sigbits))


cidr4_inuse = namedtuple('cidr4_inuse', 'cidr4 inuse')


def convert_cidr4_list_to_contiguous_cidr4s(cidr4_inuse_list):
    """
    Supply list of cidr4 IPs, get list of cidr_inuse blocks in return.

    >>> list(convert_cidr4_list_to_contiguous_cidr4s([
    ...     cidr4('1.2.3.10/32'),
    ...     cidr4('1.2.3.11/32'),
    ...     cidr4('1.2.3.12/32'),
    ...     cidr4('1.2.3.13/32'),
    ...     cidr4('1.2.3.14/32'),
    ...     cidr4('1.2.3.15/32'),
    ...     cidr4('1.2.3.16/32'),
    ...     cidr4('1.2.3.4/32'),
    ...     cidr4('1.2.3.5/32'),
    ...     cidr4('1.2.3.6/32'),
    ...     cidr4('1.2.3.8/32')]))
    [cidr4_inuse(cidr4=cidr4("1.2.3.0/30"), inuse=False), \
cidr4_inuse(cidr4=cidr4("1.2.3.4/31"), inuse=True), \
cidr4_inuse(cidr4=cidr4("1.2.3.6"), inuse=True), \
cidr4_inuse(cidr4=cidr4("1.2.3.7"), inuse=False), \
cidr4_inuse(cidr4=cidr4("1.2.3.8"), inuse=True), \
cidr4_inuse(cidr4=cidr4("1.2.3.9"), inuse=False), \
cidr4_inuse(cidr4=cidr4("1.2.3.10/31"), inuse=True), \
cidr4_inuse(cidr4=cidr4("1.2.3.12/30"), inuse=True), \
cidr4_inuse(cidr4=cidr4("1.2.3.16"), inuse=True), \
cidr4_inuse(cidr4=cidr4("1.2.3.17"), inuse=False), \
cidr4_inuse(cidr4=cidr4("1.2.3.18/31"), inuse=False), \
cidr4_inuse(cidr4=cidr4("1.2.3.20/30"), inuse=False), \
cidr4_inuse(cidr4=cidr4("1.2.3.24/29"), inuse=False), \
cidr4_inuse(cidr4=cidr4("1.2.3.32/27"), inuse=False), \
cidr4_inuse(cidr4=cidr4("1.2.3.64/26"), inuse=False), \
cidr4_inuse(cidr4=cidr4("1.2.3.128/25"), inuse=False)]
    """
    ips = list(sorted(cidr4_inuse_list))

    # Group IPs per class_c
    class_cs = []
    class_c = None
    ips_new = []
    for ip in ips:
        assert ip.sigbits == 32, ip
        class_c_new = ip.address & 0xffffff00
        if class_c_new != class_c:
            if ips_new:
                class_cs.append(ips_new)
            ips_new = []
            class_c = class_c_new
        ips_new.append(ip)
    if ips_new:
        class_cs.append(ips_new)

    # Loop over found class_cs, and yield inuse/not-inuse blocks.
    for ips in class_cs:
        first = ips[0].truncated(24)
        last = None
        for ip in ips:
            if last is None:
                for c in cidr4.generate_cidr4_list_from_start_end(
                        first.address, ip.address):
                    yield cidr4_inuse(c, False)
                first = last = ip
            elif ip.address == last.address + 1:
                last = ip
            else:
                for c in cidr4.generate_cidr4_list_from_start_end(
                        first.address, last.address + 1):
                    yield cidr4_inuse(c, True)
                for c in cidr4.generate_cidr4_list_from_start_end(
                        last.address + 1, ip.address):
                    yield cidr4_inuse(c, False)
                first = last = ip
        for c in cidr4.generate_cidr4_list_from_start_end(
                first.address, last.address + 1):
            yield cidr4_inuse(c, True)
        for c in cidr4.generate_cidr4_list_from_start_end(
                last.address + 1, last.truncated(24).next().address):
            yield cidr4_inuse(c, False)


# Example:
#
# buf = sys.stdin.read()
# ips = [cidr4(ip) for ip in buf.split()]
# for ci in convert_cidr4_list_to_contiguous_cidr4s(ips):
#     if sys.argv[1:2] == ['--verbose']:
#         cs = ci.cidr4.as_list()
#     else:
#         cs = [ci.cidr4]
#     if ci.inuse:
#         for c in cs:
#             print('        %-20s  %s' % (c, c.as_from_to()))
#     else:
#         for c in cs:
#             print('FREE    %-20s  %s' % (c, c.as_from_to()))


if __name__ == '__main__':
    import doctest
    doctest.testmod()
