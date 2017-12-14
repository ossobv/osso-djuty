# vim: set ts=8 st=4 sts=4 et ai:
from django.http import HttpResponse
from django.utils.translation import ugettext_lazy as _
from osso.core.views import simple_form_view
from osso.sms.backends.sms_wireless.forms import DeliveryReportForm, IncomingTextMessageForm, \
        DeliveryReportForwardForm


WIRELESS_IPS = (
    '212.204.209.161', '213.206.93.16', '194.140.246.82',
)


class HttpResponseOk(HttpResponse):
    def __init__(self, message=None, saved=None):
        super(HttpResponseOk, self).__init__(content=u'[RESPONSE-OK]', content_type='text/plain; charset=UTF-8')


class HttpResponseFail(HttpResponse):
    def __init__(self, message='(unknown)'):
        super(HttpResponseFail, self).__init__(content=u'[RESPONSE-ERROR: %s]' % message, content_type='text/plain; charset=UTF-8')


def incoming_text(request):
    return simple_form_view(request, form_class=IncomingTextMessageForm, heading=_(u'Incoming SMS'),
            ip_whitelist=WIRELESS_IPS, httpresponse_ok=HttpResponseOk, httpresponse_fail=HttpResponseFail, mail_on_fail=True)


def delivery_report(request):
    return simple_form_view(request, form_class=DeliveryReportForm, heading=_(u'Delivery report'),
            ip_whitelist=WIRELESS_IPS, httpresponse_ok=HttpResponseOk, httpresponse_fail=HttpResponseFail, mail_on_fail=True)


def delivery_report_forward(request):
    if request.method == 'POST':
        form = DeliveryReportForwardForm(data=request.POST)
        if form.is_valid():
            response = form.forward(request)
            return HttpResponse(response, content_type='text/plain; charset=UTF-8')
        form.log(request)
        return HttpResponseOk()
    return simple_form_view(request, form_class=DeliveryReportForwardForm, heading=_(u'Delivery report forward'),
            ip_whitelist=WIRELESS_IPS, httpresponse_ok=HttpResponseOk, httpresponse_fail=HttpResponseFail, mail_on_fail=True)
