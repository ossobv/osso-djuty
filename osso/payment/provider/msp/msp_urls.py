# vim: set ts=8 sw=4 sts=4 et ai:
from osso.payment.provider.msp.msp_views import (TransactionAbort,
    TransactionReport, TransactionReturn)

try:  # Django 1.4+
    from django.conf.urls import patterns, url
except ImportError:  # Django 1.3-
    from django.conf.urls.defaults import patterns, url


# We expect this to be included as ^api/msp/
urlpatterns = patterns('',
    # URL: http://SOMEWHERE/api/msp/PAYMENTID/return/
    # Here we have to call the msp API and check that the payment
    # succeeded.
    url(r'^(?P<payment_id>[0-9A-Fa-f]+)/return/$',
        TransactionReturn.as_view(), name='msp_return'),

    # URL: http://SOMEWHERE/api/msp/PAYMENTID/abort/
    # Abort/cancel the transaction.
    url(r'^(?P<payment_id>[0-9A-Fa-f]+)/abort/$',
        TransactionAbort.as_view(), name='msp_abort'),

    # URL: http://SOMEWHERE/api/msp/report/?transactionid=1234
    # You need to put the URL in the MSP merchant configuration as well.
    url(r'^report/$',
        TransactionReport.as_view(), name='msp_report'),
)
