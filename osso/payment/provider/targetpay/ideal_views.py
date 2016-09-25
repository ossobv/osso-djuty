# vim: set ts=8 sw=4 sts=4 et ai tw=79:
import traceback

from django.core.mail import mail_admins
from django.http import HttpResponse, Http404
from django.views.generic import RedirectView, View

from osso.autolog.utils import log
from osso.payment import use_test_mode
from osso.payment.models import Payment
from osso.payment.signals import payment_updated
from osso.payment.provider.targetpay.ideal import Ideal


class TransactionReturn(RedirectView):
    def get_redirect_url(self, payment_id):
        # Check that the user is logged in and that the payment belongs to
        # said user. If we skip this we can get user-trailing-bots hitting
        # this URL without a query_string, resulting in an assert-fail below.
        user = self.request.user
        if user.is_anonymous():
            raise Http404()  # not logged in
        try:
            payment = Payment.objects.get(id=payment_id)
        except Payment.DoesNotExist:
            raise Http404()  # does not exist
        if payment.paying_user_id != user.id:
            raise Http404()  # belongs to different user

        # Thusfar, we've always gotten the trxid via the GET too.
        assert self.request.GET.get('trxid') == payment.unique_key

        if payment.is_success is None:
            next_url = payment.get_url('toosoon')
        elif payment.is_success:
            next_url = payment.get_url('success')
        else:
            next_url = payment.get_url('abort')

        return next_url


class TransactionAbort(RedirectView):
    def get_redirect_url(self, payment_id):
        # Check that the user is logged in and that the payment belongs to
        # said user. If we skip this we can get user-trailing-bots hitting
        # this URL without a query_string, resulting in an assert-fail below.
        user = self.request.user
        if user.is_anonymous():
            raise Http404()  # not logged in
        try:
            payment = Payment.objects.get(id=payment_id)
        except Payment.DoesNotExist:
            raise Http404()  # does not exist
        if payment.paying_user_id != user.id:
            raise Http404()  # belongs to different user

        # Thusfar, we've always gotten the trxid via the GET too.
        assert self.request.GET.get('trxid') == payment.unique_key

        # # Don't do these. They are handled through the /report/ URL.
        # payment.mark_aborted()
        # payment_updated.send(sender=payment, change='aborted')

        return payment.get_url('abort')


class TransactionReport(View):
    """
    This view is called by the Targetpay backend... whenever there is a
    status update.

    The docs mention nothing about our response, so an 'OK' with a 200
    should probably be good.
    """
    def post(self, request, payment_id):
        log(repr(request.POST), 'targetpay', 'report')

        content_type = 'text/plain; charset=UTF-8'
        unique_key = request.POST.get('trxid')
        try:
            payment = Payment.objects.get(id=payment_id)
            if payment.unique_key != unique_key:
                raise Payment.DoesNotExist('bad trxid?')
        except Payment.DoesNotExist as e:
            mail_admins('Check failed at Targetpay TransactionReport',
                        (u'Exception: %s (%r)\n\nGet: %r\n\nPost: %r\n\n'
                         u'Meta: %r' %
                         (e, e, request.GET, request.POST, request.META)))
            response = HttpResponse('NAK', content_type=content_type)
            response.status_code = 500
            return response

        targetpay = Ideal(testing=use_test_mode())
        try:
            targetpay.request_status(payment, request)
        except Exception as e:
            mail_admins(('Replying with NAK to bad message from '
                         'Targetpay (might indicate a problem)'),
                        (u'Exception: %s (%s)\n\nGet: %r\n\nPost: %r\n\n'
                         u'Traceback: %s\n\nMeta: %r' %
                         (e, e, request.GET, request.POST,
                          traceback.format_exc(), request.META)))
            response = HttpResponse('NAK', content_type=content_type)
            response.status_code = 500
            return response

        return HttpResponse('OK', content_type=content_type)
