# vim: set ts=8 sw=4 sts=4 et ai:
from django.contrib import admin
from osso.userchat.models import Channel, Message


class ChannelAdmin(admin.ModelAdmin):
    list_display = ('name', 'relation', 'relation_id')

    def relation_id(self, object):
        return object.relation_id


admin.site.register(Channel, ChannelAdmin)
admin.site.register(Message)
