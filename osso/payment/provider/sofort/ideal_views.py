# vim: set ts=8 sw=4 sts=4 et ai:
from hashlib import sha256
from django.conf import settings
from django.core.mail import mail_admins
from django.core.urlresolvers import reverse
from django.http import HttpResponse
from django.views.generic import RedirectView, View
from osso.payment.models import Payment
from osso.payment.provider.sofort.ideal import Ideal
from osso.payment.xmlutils import xmlescape


class TransactionPassed(RedirectView):
    def get_redirect_url(self, payment_id, transaction_hash):
        try:
            payment = Payment.objects.get(id=payment_id)
        except Payment.DoesNotExist as e:
            pass
        else:
            ideal = Ideal(testing=settings.OSSO_PAYMENT.get('test_mode',
                                                            False))
            try:
                ideal.process_passed(payment, transaction_hash)
            except Exception as e:
                pass
            else:
                # Return to a success url where we can celebrate
                return payment.get_url('success')

        mail_admins(
            u'Check failed at sofort/ideal transaction_passed',
            u'Exception: %s (%r)\n\nGet: %r\n\nPost: %r\n\nMeta: %r' % (
                e, e, self.request.GET, self.request.POST, self.request.META
            )
        )
        return '/?fail'


class TransactionAborted(RedirectView):
    def get_redirect_url(self, payment_id, transaction_key):
        try:
            payment = Payment.objects.get(id=payment_id)
        except Payment.DoesNotExist as e:
            pass
        else:
            ideal = Ideal(testing=settings.OSSO_PAYMENT.get('test_mode',
                                                            False))
            try:
                ideal.process_aborted(payment, transaction_key)
            except Exception as e:
                pass
            else:
                # Return to a abort url where we can wipe our tears
                return payment.get_url('abort')

        mail_admins(
            u'Check failed at sofort/ideal transaction_aborted',
            u'Exception: %s (%r)\n\nGet: %r\n\nPost: %r\n\nMeta: %r' % (
                e, e, self.request.GET, self.request.POST, self.request.META
            )
        )
        return '/?fail'


class TransactionReport(RedirectView):
    # FIXME: should be a POST-accepting-only view without a form
    # IMPORTANT, MUST FIX THIS BEFORE PRODUCTION
    pass


class FakeIdeal(View):
    def post(self, request, **kwargs):
        # kwargs contains bank_code, but we're not doing anything with
        # that right now.
        # kwargs['bank_code']

        # Create validation URL from user_variable_{0,1} and our secret:
        user_variable_0 = request.POST.get('user_variable_0', '')
        user_variable_1 = request.POST.get('user_variable_1', '')
        if not user_variable_0.isdigit() or user_variable_1 == '':
            raise TypeError('Someone is messing with us.')
        project_password = (getattr(settings, 'OSSO_PAYMENT_SOFORT', {})
                            .get('project_password', '').encode('utf-8'))
        user_variable_1_hash_pass = sha256('%s%s' % (
            user_variable_1.encode('utf-8'),
            project_password
        )).hexdigest()

        # Display a page where we can choose what "has happened" and
        # redirect to the appropriate place.
        base_url = ''
        path = reverse('sofort_ideal_passed',
                       kwargs={'payment_id': user_variable_0,
                               'transaction_hash': user_variable_1_hash_pass})
        passed_url = '%s%s' % (base_url, path)

        path = reverse('sofort_ideal_aborted',
                       kwargs={'payment_id': user_variable_0,
                               'transaction_key': user_variable_1})
        aborted_url = '%s%s' % (base_url, path)

        message = '''<h1>Sofort FAKE iDEAL</h1>
        <dl>
            <dt>Regarding</dt>
            <dd>%(description)s</dd>
            <dt>Amount:</dt>
            <dd>%(amount)s</dd>
        </dl>
        <p>
            <a href="%(passed_url)s">Passed</a> or
            <a href="%(aborted_url)s">Aborted</a>
        </p>
        ''' % {
            'description': xmlescape(request.POST.get('reason_1', '')),
            'amount': xmlescape(request.POST.get('amount', '')),
            'passed_url': xmlescape(passed_url, '"'),
            'aborted_url': xmlescape(aborted_url, '"'),
        }

        return HttpResponse(message, content_type='text/html; charset=UTF-8')
