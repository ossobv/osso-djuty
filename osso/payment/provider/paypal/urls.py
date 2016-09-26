# vim: set ts=8 sw=4 sts=4 et ai:
from osso.payment.conditional import patterns, url

from .paypal_views import (
    TransactionPassed, TransactionAborted)


# We expect this to be included as ^api/paypal/
urlpatterns = patterns('',  # noqa
    # URL: http://SOMEWHERE/api/paypal/PAYMENTID/cont/
    # Here we have to call the paypal API and check that the payment
    # succeeded.
    url(r'^(?P<payment_id>[0-9A-Fa-f]+)/cont/$',
        TransactionPassed.as_view(), name='paypal_passed'),

    # URL: http://SOMEWHERE/api/paypal/PAYMENTID/stop/
    url(r'^(?P<payment_id>[0-9A-Fa-f]+)/stop/$',
        TransactionAborted.as_view(), name='paypal_aborted'),
)
