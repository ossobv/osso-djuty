# vim: set ts=8 sw=4 sts=4 et ai:
from django.views.decorators.csrf import csrf_exempt

from osso.payment.conditional import patterns, url

from .ideal_views import (
    TransactionAbort, TransactionReport, TransactionReturn)


# We expect this to be included as ^api/targetpay/
urlpatterns = patterns('',  # noqa
    # URL: http://SOMEWHERE/api/targetpay/PAYMENTID/return/
    # We expect ?trxid={...}&idealtrxid={...}&ec={...} as GET params.
    url(r'^(?P<payment_id>[0-9A-Fa-f]+)/return/$',
        TransactionReturn.as_view(), name='targetpay_return'),

    # URL: http://SOMEWHERE/api/targetpay/PAYMENTID/abort/
    # Abort/cancel the transaction.
    url(r'^(?P<payment_id>[0-9A-Fa-f]+)/abort/$',
        TransactionAbort.as_view(), name='targetpay_abort'),

    # URL: http://SOMEWHERE/api/targetpay/PAYMENTID/report/
    # > Als u deze invult, dan roepen we de URL op uw server aan na de
    # > betaling (vanaf onze server). Dit gebeurt ook als uw klant niet
    # > op de knop 'Verder klikte...'. Aan uw URL voegen we 6 parameters
    # > toe:
    # > - trxid met daarin het bestelnummer
    # > - idealtrxid met het iDEAL betaalkenmerk
    # > - rtlo met de layoutcode
    # > - status met een van de resultaatcodes uit 5.2.
    # > - cname met de klantnaam, mits de betaling gelukt is
    # > - cbank met de klantbank, mits de betaling gelukt is
    url(r'^(?P<payment_id>[0-9A-Fa-f]+)/report/$',
        csrf_exempt(TransactionReport.as_view()), name='targetpay_report'),
)
