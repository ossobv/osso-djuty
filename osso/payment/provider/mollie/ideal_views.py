# vim: set ts=8 sw=4 sts=4 et ai:
from django.conf import settings
from django.core.mail import mail_admins
from django.http import HttpResponse
from django.views.generic import RedirectView, View
from osso.payment.models import Payment
from osso.payment.provider.mollie.ideal import Ideal


class TransactionReturn(RedirectView):
    def get_redirect_url(self, payment_id):
        try:
            payment = Payment.objects.get(id=payment_id)
        except Payment.DoesNotExist as e:
            pass
        else:
            # We get transaction_id in the URL.. check it.. because we
            # can.
            transaction_id = (self.request.GET.get('transaction_id')
                              .encode('ascii', 'replace'))
            if str(payment.unique_key.rsplit('-', 1)[0]) == transaction_id:
                # If all is well, the transaction_report url has already
                # been called. That means there's either payment success
                # or payment failure. This isn't 100% proof though.
                # If status is still submitted/unknown, we must be prepared
                # to tell the user that that is the case.
                if payment.is_success is None:
                    next_url = payment.get_url('toosoon')
                elif payment.is_success:
                    next_url = payment.get_url('success')
                else:
                    next_url = payment.get_url('abort')

                return next_url
            else:
                e = ValueError('Mismatch of transaction_id in GET')

        mail_admins(
            u'Check failed at mollie/ideal transaction_return',
            u'Exception: %s (%r)\n\nGet: %r\n\nPost: %r\n\nMeta: %r' % (
                e, e, self.request.GET, self.request.POST, self.request.META
            )
        )
        return '/?fail'


class TransactionReport(View):
    '''
    This view is called by the Mollie backend while the user is still
    on the payment page.

    The only relevant output is the HTTP status code.
    '''
    def get(self, request, payment_id):
        content_type = 'text/plain; charset=UTF-8'

        try:
            payment = Payment.objects.get(id=payment_id)
        except Payment.DoesNotExist as e:
            pass
        else:
            transaction_id = self.request.GET.get('transaction_id')
            testing = settings.OSSO_PAYMENT.get('test_mode', False)
            ideal = Ideal(testing=testing)
            try:
                ideal.process_report(payment, transaction_id)
            except Exception as e:
                # XXX/FIXME: here we should:
                # (a) do the lookup
                # (b) if the lookup says 'aborted', we can rest
                # (c) if the lookup says 'paid', we have a problem
                mail_admins(('Replying with NAK to bad message from Mollie '
                             '(might indicate a problem)'),
                            (u'Exception: %s (%s)\n\nGet: %r\n\nPost: %r\n\n'
                             u'Meta: %r' %
                             (e, e, self.request.GET, self.request.POST,
                              self.request.META)))
                response = HttpResponse('NAK', content_type=content_type)
                response.status_code = 500
                return response
            else:
                return HttpResponse('OK', content_type=content_type)

        mail_admins(u'Check failed at mollie/ideal transaction_report',
                    (u'Exception: %s (%s)\n\nGet: %r\n\nPost: %r\n\nMeta: %r' %
                     (e, e, self.request.GET, self.request.POST,
                      self.request.META)))
        response = HttpResponse('NAK', content_type=content_type)
        response.status_code = 500
        return response
