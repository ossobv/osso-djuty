# vim: set ts=8 sw=4 sts=4 et ai:
import json
from urllib import urlencode

from osso.core.http.shortcuts import http_get
from osso.payment import (
    BuyerError, PaymentAlreadyUsed, PaymentSuspect,
    ProviderError, ProviderBadConfig, ProviderDown)
from osso.payment.base import IdealProvider
from osso.payment.conditional import log, reverse, settings
from osso.payment.signals import payment_updated


class TargetpayIdeal(IdealProvider):
    def __init__(self, testing=False, rtlo=None):
        self.provider_url = 'https://www.targetpay.com'
        self.rtlo = (
            rtlo or
            getattr(settings, 'OSSO_PAYMENT_TARGETPAY', {}).get('rtlo'))
        self.test_mode = testing

    def start_transaction(self, payment, build_absolute_uri):
        parameters = {
            'rtlo': self.rtlo,
            'description': payment.description,
            'amount': int(payment.amount * 100),
            'returnurl': build_absolute_uri(reverse(
                'osso_payment_targetpay_return',
                kwargs={'payment_id': payment.id})),
            'cancelurl': build_absolute_uri(reverse(
                'osso_payment_targetpay_abort',
                kwargs={'payment_id': payment.id})),
            'reporturl': build_absolute_uri(reverse(
                'osso_payment_targetpay_report',
                kwargs={'payment_id': payment.id})),
            'ver': '3',
        }
        if self.test_mode:
            # > Om uw orderafhandeling te testen kunt u bij de start
            # > functie uit paragraaf 3 de parameter
            # > test=1 opgeven. Met deze instelling krijgt u altijd een
            # > '00000 OK' status terug wanneer u de check functie uit
            # > paragraaf 5 aanroept.
            # You'll return to the returnurl.
            parameters['test'] = '1'

        # https://www.targetpay.com/ideal/start?rtlo=$NUMBER&
        #   description=test123&amount=123&
        #   returnurl=https://$HOST/return&
        #   cancelurl=https://$HOST/cancel&
        #   reporturl=https://$HOST/report&test=1&ver=3
        ret = self._do_request('/ideal/start', parameters)
        # 000000 177XXX584|https://www.targetpay.com/ideal/launch?
        #   trxid=177XXX584&ec=779XXXXXXXXX273
        if ' ' in ret:
            status, rest = ret.split(' ', 1)
        else:
            assert status != '000000', ret

        if status != '000000':
            self.handle_error(payment, ret)
            assert False

        try:
            trxid, payment_url = rest.split('|', 1)
            if not payment_url.startswith('https:'):
                raise ValueError('no https?')
        except ValueError:
            self.handle_error(payment, ret)
            assert False

        # Initiate it and store the unique_key.
        # (Does an atomic check.)
        payment.set_unique_key(trxid)

        return payment_url

    def get_payment_form(self, payment):
        """
        Return the verbatim HTML form that should be (auto)submitted by
        the user to go to the payment page.
        """
        host_prefix = payment.realm
        if '://' not in host_prefix:
            host_prefix = 'http://%s' % (host_prefix,)
        build_absolute_uri = (lambda x: host_prefix + x)

        if payment.transfer_initiated:
            raise PaymentAlreadyUsed()  # user clicked back?

        payment_url = self.start_transaction(payment, build_absolute_uri)

        return self.create_html_form_from_url(payment_url, 'targetpay_form')

    def request_status(self, payment, request):
        """
        Check status at payment backend and store value locally.
        """
        parameters = {
            'rtlo': self.rtlo,
            'trxid': payment.unique_key,
            # > Als u voor once '1' invult dan zal slechts 1x een OK status
            # > teruggegeven worden.  Als de bovenstaande URL nog een keer
            # > wordt aangeroepen voor hetzelfde Transactie ID dan krijgt u
            # > een foutmelding 'TP00014 (Reeds ingewisseld)' terug.  Als u
            # > voor once '0' invult dan zal steeds een OK status terug
            # >blijven komen.
            'once': '0',  # no need, we use atomic db update
        }
        ret = self._do_request('/ideal/check', parameters)

        # 000000 OK
        # TP0012 Transaction has expired
        # etc..
        if ' ' in ret:
            status, rest = ret.split(' ', 1)
        else:
            assert status != '000000', ret

        if status == '000000':
            payment.mark_passed()
            payment.mark_succeeded()
            payment_updated.send(sender=payment, change='passed')
            postdata = request.POST
            payment.set_blob('targetpay.ideal: ' + json.dumps(postdata))
        elif status == 'TP0010':  # Transaction has not been completed
            assert payment.state == 'submitted', (payment.pk, payment.state)
        elif status == 'TP0011':  # Transaction has been cancelled
            payment.mark_aborted()
            payment_updated.send(sender=payment, change='aborted')
        elif status == 'TP0012':  # Transaction has expired (10 minutes)
            payment.mark_aborted()
            payment_updated.send(sender=payment, change='aborted')
        elif status == 'TP0014':  # Already used
            assert payment.state == 'final'
        else:
            # FIXME: Better exception.
            raise ValueError('bad status %s (%r) for %s' % (
                status, ret, payment.pk))

    def handle_error(self, payment, response):
        if False:  # TEMP: make flake happy
            raise BuyerError()
            raise PaymentSuspect()
            raise ProviderBadConfig()
            raise ProviderError()
            raise ProviderDown()
        # FIXME
        raise ValueError('payment: %d\nresponse: %r' % (
            payment.id, response))

    def _do_request(self, path, parameters):
        url = '{provider_url}{path}?{parameters}'.format(
            provider_url=self.provider_url, path=path,
            parameters=urlencode(parameters))

        log(url, 'targetpay', 'qry')
        ret = http_get(url)
        log(ret, 'targetpay', 'ret')

        return ret
