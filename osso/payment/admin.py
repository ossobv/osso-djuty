# vim: set ts=8 sw=4 sts=4 et ai:
from django.contrib import admin
from osso.payment.models import Payment


class PaymentAdmin(admin.ModelAdmin):
    list_display = ('id', 'paying_user', 'description', 'created', 'amount', 'state', 'is_success')


admin.site.register(Payment, PaymentAdmin)
