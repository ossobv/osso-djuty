# vim: set ts=8 st=4 sts=4 et ai:
from django.db.transaction import commit_on_success
from django.http import HttpResponse, HttpResponseServerError
from django.utils.translation import ugettext_lazy as _
from osso.core.views import simple_form_view
from osso.sms.backends.sms_zjipz.forms import IncomingTextMessageForm, DeliveryReportForm


ZJIPZ_IPS = (
    '127.0.0.1', '127.0.1.1',
)


class HttpResponseOk(HttpResponse):
    def __init__(self, message=None, saved=None):
        super(HttpResponseOk, self).__init__(content=u'OK', content_type='text/plain; charset=UTF-8')


class HttpResponseFail(HttpResponseServerError):
    def __init__(self, message='(unknown)'):
        super(HttpResponseFail, self).__init__(content=u'ERROR: %s' % message, content_type='text/plain; charset=UTF-8')


@commit_on_success
# Prevent the message from being stored if an incoming_message signal
# handler breaks. The sender will have to redo the sending.
def incoming_text(request):
    return simple_form_view(request, form_class=IncomingTextMessageForm, heading=_(u'Incoming SMS'),
            ip_whitelist=ZJIPZ_IPS, httpresponse_ok=HttpResponseOk, httpresponse_fail=HttpResponseFail, mail_on_fail=True)


@commit_on_success
def delivery_report(request):
    return simple_form_view(request, form_class=DeliveryReportForm, heading=_(u'Delivery report'),
            ip_whitelist=ZJIPZ_IPS, httpresponse_ok=HttpResponseOk, httpresponse_fail=HttpResponseFail, mail_on_fail=True)
