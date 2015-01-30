# vim: set ts=8 sw=4 sts=4 et ai:
from django.contrib import admin
from osso.sms.models import OperatorCountryCode, Operator, Payout, TextMessage, TextMessageExtra


class PayoutAdmin(admin.ModelAdmin):
    list_display = ('operator', 'local_address', 'tariff_cent', 'payout_cent')


class TextMessageAdmin(admin.ModelAdmin):
    list_display = ('id', 'remote_address', 'local_address', 'status', 'created', 'trimmed_body')
    search_fields = ('remote_address',)

    def trimmed_body(self, object):
        return object.body[0:24] + ('', ' ...')[len(object.body) > 24]


class TextMessageExtraAdmin(admin.ModelAdmin):
    raw_id_fields = ('textmessage',)


admin.site.register(OperatorCountryCode)
admin.site.register(Operator)
admin.site.register(Payout, PayoutAdmin)
admin.site.register(TextMessage, TextMessageAdmin)
admin.site.register(TextMessageExtra, TextMessageExtraAdmin)
