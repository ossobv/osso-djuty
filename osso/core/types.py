# vim: set ts=8 sw=4 sts=4 et ai:
# We won't work on ancient (32-bit) systems where int!=long and 32 bits
# is the max integer.  Either use 64-bit or a newer python.  We need
# this check, because 0xffffffffL ('L') doesn't work anymore in
# python3.
if 0xffffffff == -1:
    raise NotImplementedError()


__all__ = ('cidr4',)


class _ComparableMixin(object):
    """Python3 does not do the __cmp__ method :("""
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


class cidr4(_ComparableMixin):
    '''
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
    >>> a, b = cidr4('1.64.255.128/32'), cidr4('1.64.255.128')
    >>> a == b and a <= b and a >= b
    True
    >>> b = cidr4('1.64.255.128/25') # larger subnet sorts earlier
    >>> b < a and b != a and not (b > a)
    True
    >>> c = cidr4('2.0.0.0/7')
    >>> c > b and c > a
    True
    >>> try: cidr4('aap')
    ... except: pass
    ... else: assert False
    >>> try: cidr4('1.2.3.4/29') # .4 may have significant bits in (30, 31, 32)
    ... except: pass
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
    '''
    __slots__ = ('address', 'sigbits')

    def __init__(self, value):
        if isinstance(value, cidr4):
            self.address, self.sigbits = value.address, value.sigbits
            return

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
                print('hier!'), netmask
                raise ValueError('Invalid netmask.')
        # 1.2.3.0/24
        else:
            sigbits = int(sigbits)  # may raise ValueError

        # may raise ValueError:
        a, b, c, d = [int(byte) for byte in host.split('.', 4)]
        if a < 0 or a > 255 or b < 0 or b > 255 or c < 0 or c > 255 or d < 0 or d > 255 \
                or sigbits < 0 or sigbits > 32:
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
        except:
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

    def __repr__(self):
        return 'cidr4("%s")' % self.__str__()

    def __str__(self):
        return self.as_string(ip_as_net=False)

    def __contains__(self, subset):
        if self.sigbits > subset.sigbits:  # more bits is smaller
            return False
        netmask = (0xffffffff << (32 - self.sigbits)) & 0xffffffff
        return (subset.address & netmask) == self.address

    def as_string(self, ip_as_net=True):
        return '%d.%d.%d.%d%s' % (
            (self.address >> 24) & 0xff,
            (self.address >> 16) & 0xff,
            (self.address >> 8) & 0xff,
            (self.address) & 0xff,
            ('', '/%d' % self.sigbits)[ip_as_net or self.sigbits != 32]
        )

    def as_verbose_string(self, ip_as_net=True):
        if self.sigbits == 32 and not ip_as_net:
            return self.as_string(False)

        netmask = (0xffffffff << (32 - self.sigbits)) & 0xffffffff
        return '%d.%d.%d.%d/%d.%d.%d.%d' % (
            (self.address >> 24) & 0xff,
            (self.address >> 16) & 0xff,
            (self.address >> 8) & 0xff,
            (self.address) & 0xff,
            (netmask >> 24) & 0xff,
            (netmask >> 16) & 0xff,
            (netmask >> 8) & 0xff,
            (netmask) & 0xff
        )
