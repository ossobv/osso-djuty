# vim: set ts=8 sw=4 sts=4 et ai tw=79:
import traceback

from django.http import HttpResponse, Http404
from django.views.generic import RedirectView, View

from osso.payment.conditional import mail_admins
from osso.payment.models import Payment

from .msp import ProviderIsInactive
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

        # Thusfar, we've always gotten the transaction_id via the GET too.
        # It's not necessary, but it's nice to know that no one is changing the
        # APIs.
        assert payment_id == self.request.GET.get('transactionid')

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

        # Thusfar, we've always gotten the transaction_id via the GET too.
        # It's not necessary, but it's nice to know that no one is changing the
        # APIs.
        assert payment_id == self.request.GET.get('transactionid')

        # Don't trust the user. Call and look up the result.
        msp = get_instance()
        msp.request_status(payment)

        if payment.is_success is False:
            # Excellent. MSP returns cancelled if the user pressed the
            # Abort button...
            pass

        elif payment.is_success is None:
            # ... except sometimes, when MSP simply returns "initialized"
            # when the user got here and requests an abort. And after a
            # while we get "expired" (which we cannot process for reasons
            # mentioned in msp.py).
            # If the payment wasn't touched, touch it ourselves.
            # NO WAIT! DID I MENTION THAT MSP CAN RE-OPEN TRANSACTIONS?
            # IGNORE! IGNORE! See also the #DO_NOT_DO# lines in msp.py.
            # #DO_NOT_DO#payment.mark_aborted()
            # #DO_NOT_DO#payment_updated.send(sender=payment, change='aborted')
            pass

        else:
            # Something went wrong in request_status or the user is messing
            # with us.
            raise Exception('User abort of payment %d failed' %
                            (payment.id,))

        return payment.get_url('abort')


class TransactionReport(View):
    """
    This view is called by the MSP backend... whenever there is a status
    update.

    The only relevant output is the 'OK' string.

    "Als u de notificatie correct heeft verwerkt dient u als antwoord op
    het verzoek de tekst "OK" te geven. Als er iets fout is gegaan, dan
    geeft u een ander antwoord als [sic!] "OK" (bijvoorbeeld een
    foutmelding). Het verzoek wordt dan tot drie keer herhaald, en de
    melding wordt gelogd."
    """
    def get(self, request):
        content_type = 'text/plain; charset=UTF-8'
        payment_id = request.GET.get('transactionid')

        try:
            payment = Payment.objects.get(id=payment_id)
        except Payment.DoesNotExist as e:
            pass
        else:
            msp = get_instance()
            try:
                msp.request_status(payment)
            except Exception as e:
                is_inactive = isinstance(e, ProviderIsInactive)
                reply = 'OK' if is_inactive else 'NAK'
                payinfo = {
                    'id': payment.id,
                    'created': payment.created,
                    'is_success': payment.is_success,
                    'blob': payment.blob,
                }
                mail_admins((u'Replying with %s to MSP report [%s, %s, %s] '
                             u'(might indicate a problem)' % (
                                 reply, payment.id, payment.is_success,
                                 payment.created)),
                            (u'Exception: %s (%s)\n\nGet: %r\n\nPost: %r\n\n'
                             u'Traceback: %s\n\nMeta: %r\n\nPayment: %r' % (
                                 e, e, request.GET, request.POST,
                                 traceback.format_exc(), request.META,
                                 payinfo)))
                response = HttpResponse(reply, content_type=content_type)
                response.status_code = 500
                return response
            else:
                return HttpResponse('OK', content_type=content_type)

        # WTF is Apple doing? Ignore requests that have no transactionid.
        # User-Agent:
        #   Mozilla/5.0 (Windows NT 6.1; WOW64) AppleWebKit/537.36
        #   (KHTML, like Gecko) Chrome/31.0.1623.0 Safari/537.36"
        # Referer:
        #   (nothing)
        # Requests:
        #   17.142.152.15 - - [09/Jan/2015:01:49:47 +0100]
        #     "GET /api/msp/report HTTP/1.1" 301 0
        #   17.142.152.15 - - [09/Jan/2015:01:49:48 +0100]
        #     "GET /api/msp/report/ HTTP/1.1" 500 3
        #   17.142.152.15 - - [09/Jan/2015:01:49:48 +0100]
        #     "GET /api/msp/report/ HTTP/1.1" 500 3
        #   17.142.149.128 - - [10/Jan/2015:04:28:43 +0100]
        #     "GET /api/msp/report HTTP/1.1" 301 0
        #   17.142.149.128 - - [10/Jan/2015:04:28:46 +0100]
        #     "GET /api/msp/report/ HTTP/1.1" 500 3
        #   17.142.149.128 - - [10/Jan/2015:04:28:46 +0100]
        #     "GET /api/msp/report/ HTTP/1.1" 500 3
        #   17.142.148.235 - - [10/Jan/2015:10:49:36 +0100]
        #     "GET /api/msp/report HTTP/1.1" 301 0
        #   17.142.148.235 - - [10/Jan/2015:10:49:37 +0100]
        #     "GET /api/msp/report/ HTTP/1.1" 500 3
        #   17.142.148.235 - - [10/Jan/2015:10:49:38 +0100]
        #     "GET /api/msp/report/ HTTP/1.1" 500 3
        #   17.142.151.101 - - [10/Jan/2015:18:33:14 +0100]
        #     "GET /api/msp/report HTTP/1.1" 301 0
        #   17.142.151.101 - - [10/Jan/2015:18:33:15 +0100]
        #     "GET /api/msp/report/ HTTP/1.1" 500 3
        #   17.142.151.101 - - [10/Jan/2015:18:33:15 +0100]
        #     "GET /api/msp/report/ HTTP/1.1" 500 3
        # That's in the apple range:
        #    17.0.0.0/8 (APPLE-WWNET), the hosts don't have a PTR.
        # This is supposed to be an internal URI for the MSP provider
        # only...
        if payment_id:
            mail_admins('Check failed at msp/msp transaction_report',
                        (u'Exception: %s (%r)\n\nGet: %r\n\nPost: %r\n\n'
                         u'Meta: %r' %
                         (e, e, request.GET, request.POST, request.META)))
        response = HttpResponse('NAK', content_type=content_type)
        response.status_code = 500
        return response
