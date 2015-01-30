from django.contrib import admin
from osso.sms.backends.sms_wireless.models import DeliveryReportForward, DeliveryReportForwardLog

class DeliveryReportForwardAdmin(admin.ModelAdmin):
    list_display = ('batch_prefix', 'destination')

class DeliveryReportForwardLogAdmin(admin.ModelAdmin):
    list_display = ('datetime', 'batch_prefix', 'destination', 'response')

admin.site.register(DeliveryReportForward, DeliveryReportForwardAdmin)
admin.site.register(DeliveryReportForwardLog, DeliveryReportForwardLogAdmin)
