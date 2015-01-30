# vim: set ts=8 sw=4 sts=4 et ai:
from django.views.decorators.csrf import csrf_exempt
from osso.payment.provider.sofort.ideal_views import (TransactionPassed,
    TransactionAborted, TransactionReport, FakeIdeal)

try:  # Django 1.4+
    from django.conf.urls import patterns, url
except ImportError:  # Django 1.3-
    from django.conf.urls.defaults import patterns, url


# We expect this to be included as ^api/sofort/
urlpatterns = patterns('',
    # URL: http://SOMEWHERE/api/sofort/-USER_VAR_0-/idealcont/-USER_VAR_1_HASH_PASS-/
    url(r'^(?P<payment_id>[0-9A-Fa-f]+)/idealcont/(?P<transaction_hash>[0-9A-Fa-f]+)/$',
        TransactionPassed.as_view(), name='sofort_ideal_passed'),

    # We *DO* *NOT* expect the hash for the aborted case. Aborting
    # payments is easy to do lots of times and might be used to
    # discover the hash. Here we just take the unique_key verbatim.
    # URL: http://SOMEWHERE/api/sofort/-USER_VARIABLE_0-/idealstop/-USER_VARIABLE_1-/
    url(r'^(?P<payment_id>[0-9A-Fa-f]+)/idealstop/(?P<transaction_key>[0-9A-Fa-f-]+)/$',
        TransactionAborted.as_view(), name='sofort_ideal_aborted'),

    # URL: http://SOMEWHERE/api/sofort/-USER_VARIABLE_0-/idealpost/
    url(r'^(?P<payment_id>[0-9A-Fa-f]+)/idealpost/$',
        TransactionReport.as_view(), name='sofort_ideal_report'),

    # A fake iDEAL page so we can test this stuff
    url(r'^bogoideal/(?P<bank_code>\d+)/$',
        csrf_exempt(FakeIdeal.as_view()), name='sofort_fake_ideal'),
)
