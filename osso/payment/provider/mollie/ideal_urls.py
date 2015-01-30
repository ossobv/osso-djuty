# vim: set ts=8 sw=4 sts=4 et ai:
from osso.payment.provider.mollie.ideal_views import (TransactionReturn,
    TransactionReport)

try:  # Django 1.4+
    from django.conf.urls import patterns, url
except ImportError:  # Django 1.3-
    from django.conf.urls.defaults import patterns, url


# We expect this to be included as ^api/mollie/
urlpatterns = patterns('',
    # URL: http://SOMEWHERE/api/mollie/PAYMENTID/return/
    # Here we have to call the mollie API and check that the payment
    # succeeded.
    url(r'^(?P<payment_id>[0-9A-Fa-f]+)/return/$',
        TransactionReturn.as_view(), name='mollie_ideal_return'),

    # URL: http://SOMEWHERE/api/mollie/PAYMENTID/report/
    url(r'^(?P<payment_id>[0-9A-Fa-f]+)/report/$',
        TransactionReport.as_view(), name='mollie_ideal_report'),
)
