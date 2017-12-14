# vim: set ts=8 st=4 sts=4 et ai:
from django.http import HttpResponse
from django.http import HttpResponse, HttpResponseServerError
from django.utils.translation import ugettext_lazy as _
from osso.core.views import simple_form_view
from osso.sms.backends.sms_console.forms import IncomingTextMessageForm


class HttpResponseOk(HttpResponse):
    def __init__(self, message=None, saved=None):
        super(HttpResponseOk, self).__init__(content=u'OK', content_type='text/plain; charset=UTF-8')


class HttpResponseFail(HttpResponseServerError):
    def __init__(self, message='(unknown)'):
        super(HttpResponseFail, self).__init__(content=u'ERROR: %s' % message, content_type='text/plain; charset=UTF-8')


def incoming_text(request):
    return simple_form_view(request, form_class=IncomingTextMessageForm, heading=_(u'Incoming SMS'),
            httpresponse_ok=HttpResponseOk, httpresponse_fail=HttpResponseFail, mail_on_fail=True)
