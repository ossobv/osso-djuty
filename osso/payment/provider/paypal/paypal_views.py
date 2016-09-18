# vim: set ts=8 sw=4 sts=4 et ai:
from django.core.mail import mail_admins
from django.http import Http404
from django.views.generic import RedirectView
from osso.payment import ProviderError, TryDifferentPayment, use_test_mode
from osso.payment.models import Payment
from osso.payment.provider.paypal.paypal import Paypal


class TransactionPassed(RedirectView):
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

        get = self.request.GET
        paypal = Paypal(testing=use_test_mode())
        try:
            paypal.process_passed(payment, get['token'], get['PayerID'])
        except ProviderError:
            # If there is a provider error, we may want to catch
            # said error and inform the user.
            raise
        except TryDifferentPayment:
            # The user should try a different payment method. It's
            # customary to catch this (and the ProviderError) from
            # an exception handling middleware.
            raise
        except Exception as e:
            # If there is an unknown error, we won't shove a 500 in
            # the user's face but mail the admins while we send the
            # user to '/'.
            pass
        else:
            # Return to a success url where we can celebrate
            return payment.get_url('success')

        mail_admins(
            u'Check failed at paypal/paypal transaction_passed',
            u'Exception: %s (%r)\n\nGet: %r\n\nPost: %r\n\nMeta: %r' % (
                e, e, self.request.GET, self.request.POST, self.request.META
            )
        )
        return '/?fail'


class TransactionAborted(RedirectView):
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

        get = self.request.GET
        paypal = Paypal(testing=use_test_mode())
        try:
            paypal.process_aborted(payment, get['token'])
        except Exception as e:
            pass
        else:
            # Return to a abort url where we can wipe our tears
            return payment.get_url('abort')

        mail_admins(
            u'Check failed at paypal/paypal transaction_aborted',
            u'Exception: %s (%r)\n\nGet: %r\n\nPost: %r\n\nMeta: %r' % (
                e, e, self.request.GET, self.request.POST, self.request.META
            )
        )
        return '/?fail'
