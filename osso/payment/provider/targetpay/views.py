# vim: set ts=8 sw=4 sts=4 et ai tw=79:
import traceback

from django.http import HttpResponse, Http404
from django.views.generic import RedirectView, View

from osso.payment import PaymentSuspect
from osso.payment.conditional import log, mail_admins
from osso.payment.models import Payment

from .targetpay import AtomicUpdateDupe
from . import get_instance


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
        trxid = payment.unique_key.split('-', 1)[1]
        assert self.request.GET.get('trxid') == trxid, trxid

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
        trxid = payment.unique_key.split('-', 1)[1]
        assert self.request.GET.get('trxid') == trxid, trxid

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
        self.check_remote_addr(request)

        log(repr(request.POST), 'targetpay', 'report')

        content_type = 'text/plain; charset=UTF-8'
        try:
            payment = Payment.objects.get(id=payment_id)
            if payment.unique_key:
                trxid = payment.unique_key.split('-', 1)[1]
                if request.POST.get('trxid') != trxid:
                    raise Payment.DoesNotExist('bad trxid?')
            elif request.POST.get('status') == 'Expired':
                # Since aug2018, TGP started sending Expired notices for
                # 3-hour old transactions that weren't picked up.
                # Mark transaction as failed, and answer with OK.
                payment.mark_aborted()
                return HttpResponse('OK', content_type=content_type)

        except Payment.DoesNotExist as e:
            mail_admins('Check failed at TGP TransactionReport',
                        (u'Exception: %s (%r)\n\nGet: %r\n\nPost: %r\n\n'
                         u'Meta: %r' %
                         (e, e, request.GET, request.POST, request.META)))
            response = HttpResponse('NAK', content_type=content_type)
            response.status_code = 500
            return response

        provider_sub = payment.unique_key.split('-', 1)[0]
        targetpay = get_instance(provider_sub)
        try:
            targetpay.request_status(payment, request)
        except Exception as e:
            if isinstance(e, AtomicUpdateDupe):
                # "duplicate status"
                status, reply = 200, 'OK'
            else:
                status, reply = 500, 'NAK'

            payinfo = {
                'id': payment.id,
                'created': payment.created,
                'is_success': payment.is_success,
                'blob': payment.blob,
            }
            mail_admins((u'Replying with %s to TGP report [%s, %s, %s] '
                         u'(might indicate a problem)' % (
                             reply, payment.id, payment.is_success,
                             payment.created)),
                        (u'Exception: %s (%s)\n\nGet: %r\n\nPost: %r\n\n'
                         u'Traceback: %s\n\nMeta: %r\n\nPayment: %r' % (
                             e, e, request.GET, request.POST,
                             traceback.format_exc(), request.META,
                             payinfo)))
            response = HttpResponse(reply, content_type=content_type)
            response.status_code = status
            return response

        return HttpResponse('OK', content_type=content_type)

    def check_remote_addr(self, request):
        """
        Check source IP of reporter. This isn't strictly necessary because we
        never trust the POST data itself; we check the payment API anyway.
        """
        ip4 = request.META['REMOTE_ADDR']
        if ip4.lower().startswith('::ffff:'):
            ip4 = ip4[7:]

        if ip4 == '127.0.0.1':
            # For local override:
            #   curl -XPOST -d status=Success -d amount=675 -d trxid=X
            #     -d rtlo=Y https://SITE/api/targetpay/ID/report/
            #     --resolve SITE:443:127.0.0.1
            pass
        elif ip4.startswith('78.152.58.'):
            # The Targetpay IPs.
            pass
        else:
            raise PaymentSuspect('Bad reporter IP')
