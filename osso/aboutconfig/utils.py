# vim: set ts=8 sw=4 sts=4 et ai:
try:
    u, py2 = unicode, True
except NameError:
    u, py2 = str, False

from django.core.cache import cache
from django.db.models.signals import post_save
from osso.aboutconfig.models import Item


__all__ = ('CACHE_TIME', 'ConfigError', 'aboutconfig')

# TODO: add post_save signal on the Item to dirty the cache
CACHE_TIME = 300


class ConfigError(ValueError):
    """
    If the configuration value is unexpected, raise this.

    Example::

        raise ConfigError('my.setting', fetched_value,
                          "Expected an integral value, e.g. '1'")
    """
    def __init__(self, key, found_value, description):
        if isinstance(key, u):
            key = key.encode('utf-8')
        if isinstance(found_value, u):
            found_value = found_value.encode('utf-8')
        self.args = (key, found_value, description)

    def __repr__(self):
        return 'ConfigError(%r, %r, %r)' % self.args

    def __unicode__(self):
        return (u'Configuration item in AboutConfig bad/missing:\n'
                u'  lookup key  = %r\n'
                u'  found value = %r\n'
                u'%s') % self.args

    if py2:
        def __str__(self):
            return unicode(self).encode('utf-8')
    else:
        __str__ = __unicode__


def aboutconfig(key, default='', set=False):
    '''
    Search for key in the AboutConfig dictionary and return the value.
    Returns the empty string (or the supplied default value as unicode string)
    if the key is not found.

    >>> try:
    ...     u = unicode
    ... except NameError:
    ...     u = str
    >>> def eq(a, b):
    ...     return isinstance(a, u) and str(a) == b
    >>> from osso.aboutconfig.models import Item
    >>> from osso.aboutconfig.utils import aboutconfig
    >>> Item.objects.create(key='a.b.c.d.e',
    ...                     value=' \\n \\r somevalue with \\n spaces \\t ')
    <Item: a.b.c.d.e>
    >>> eq(aboutconfig('a.b.c.d.e'), 'somevalue with \\n spaces')
    True
    >>> eq(aboutconfig('abc'), '')
    True
    >>> eq(aboutconfig('abc', 'def'), 'def')
    True
    >>> eq(aboutconfig('abc', 123.456), '123.456')
    True
    >>> Item.objects.filter(key__in=('a.b.c.d.e', 'abc')).delete()
    '''
    cache_key = 'osso.aboutconfig.%s' % key

    if set:
        default = default.strip()
        cache.set(cache_key, default, CACHE_TIME)
        item, created = Item.objects.get_or_create(key=key,
                                                   defaults={'value': default})
        if not created and item.value != default:
            rows = Item.objects.filter(key=key).update(value=default)
            # backends that do not support matched/affected records
            # by update return None (pymongo)
            assert rows is None or rows == 1
        return

    value = cache.get(cache_key)
    if value is not None:
        return value
    try:
        value = Item.objects.get(key=key).value
        cache.set(cache_key, value, CACHE_TIME)
    except Item.DoesNotExist:
        value = u(default)
    return value


def _flush_cache(instance, created, **kwargs):
    # Still new? Do nothing..
    if created:
        return

    # Changed? Then we may need to flush the cache.
    cache_key = 'osso.aboutconfig.%s' % instance.key
    cache.delete(cache_key)
post_save.connect(_flush_cache, sender=Item)
