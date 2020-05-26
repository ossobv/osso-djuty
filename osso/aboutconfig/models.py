# vim: set ts=8 sw=4 sts=4 et ai:
from django.db import models
from django.utils.translation import ugettext_lazy as _
from osso.core.models import Model, SafeCharField


DATATYPE_TEXT = 1
# DATATYPE_UNDEFINED = UNDEFINED


class Item(Model):
    '''
    Generic model to dynamically store various additional database fields.

    The TEXT datatype strips excess spaces from the value at save time.

    The datatype used to be a separate model, but (a) no other data types have
    been defined since the inception of this app and (b) MongoDB does not like
    the fact that it used integers as primary keys. At the time, the best fix
    was to replace the 'datatype' foreign key with a 'datatype_id' integer.
    This maintains backwards compatibility and fixes so stuff just works on
    Mongo. As an added bonus, the save() is now quicker, because it doesn't
    have to look up the PK for TEXT any more.
    '''
    # One of DATATYPE_TEXT, ...
    datatype_id = models.IntegerField(verbose_name=_('data type'), default=1)
    # Key can be something like "asterisk.management.username"
    key = SafeCharField(_('key'), max_length=63, primary_key=True)
    # The value, stored in a text field. Other data types may at one point fix
    # type casting when using the aboutconfig() utility function.
    value = models.TextField(_('value'), blank=True)

    def save(self, *args, **kwargs):
        if self.datatype_id == DATATYPE_TEXT:
            self.value = self.value.strip()
        super().save(*args, **kwargs)

    def __str__(self):
        return self.key

    class Meta:
        ordering = ('key',)
        verbose_name = _('advanced/hidden configuration item')
        verbose_name_plural = _('advanced/hidden configuration items')
