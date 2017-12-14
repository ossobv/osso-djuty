# vim: set ts=8 st=4 sts=4 et ai:
from django.db.transaction import commit_on_success
from django.http import HttpResponse, HttpResponseServerError
from django.utils.translation import ugettext_lazy as _
from osso.core.views import simple_form_view
from osso.sms.backends.sms_mollie.forms import DeliveryReportForm, IncomingTextMessageForm


MOLLIE_IPS = (
    '212.61.160.227', '212.61.188.150', '212.61.188.154',

    # Old addresses (from before 9 feb. 2014):
    '77.245.85.229', '77.245.85.230', '77.245.85.231',

    ## Old addresses (from before 16 sept. 2012):
    #'82.94.203.80', '82.94.203.81', '82.94.203.82', '82.94.203.83',
    #'82.94.203.84', '82.94.203.85', '82.94.203.86',
)


class HttpResponseOk(HttpResponse):
    def __init__(self, message=None, saved=None):
        super(HttpResponseOk, self).__init__(content='OK', content_type='text/plain; charset=UTF-8')


class HttpResponseFail(HttpResponseServerError):
    def __init__(self, message='(unknown)'):
        super(HttpResponseFail, self).__init__(content='ERROR: %s' % message, content_type='text/plain; charset=UTF-8')


@commit_on_success
# Prevent the message from being stored if an incoming_message signal
# handler breaks causing the API to tell Mollie that it didn't receive
# the message this time.
#
# Note that nesting commit handlers is broken when I write this (april
# 2010), so if someone calls a commit() or a decorated function at some
# point during the execution of this view, the message may get saved
# after all. See also: http://code.djangoproject.com/ticket/2227
#
# This bug also affects the TransactionMiddleware, so if you use that
# you could consider removing this decorator.
def incoming_text(request):
    return simple_form_view(request, form_class=IncomingTextMessageForm, heading=_('Incoming SMS'),
            ip_whitelist=MOLLIE_IPS, httpresponse_ok=HttpResponseOk, httpresponse_fail=HttpResponseFail, mail_on_fail=True)


@commit_on_success
def delivery_report(request):
    return simple_form_view(request, form_class=DeliveryReportForm, heading=_('Delivery report'),
            ip_whitelist=MOLLIE_IPS, httpresponse_ok=HttpResponseOk, httpresponse_fail=HttpResponseFail, mail_on_fail=True)
