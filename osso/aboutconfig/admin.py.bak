# vim: set ts=8 st=4 sts=4 et ai:
from django.contrib import admin
from osso.aboutconfig.models import Item


class ItemAdmin(admin.ModelAdmin):
    list_display = ('key', 'internal_value')

    def internal_value(self, object):
        value = repr(object.value)
        return u'%s%s' % (value[:64], ('', '...')[len(value) > 64])


admin.site.register(Item, ItemAdmin)
