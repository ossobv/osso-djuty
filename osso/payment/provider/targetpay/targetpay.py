# vim: set ts=8 sw=4 sts=4 et ai:
import json
from urllib import urlencode

from osso.core.http.shortcuts import http_get
from osso.payment import (
    BuyerError, PaymentAlreadyUsed, PaymentSuspect,
    ProviderError, ProviderBadConfig, ProviderDown)
from osso.payment.base import Provider
from osso.payment.conditional import log, reverse, settings
from osso.payment.signals import payment_updated


class TargetpayBase(object):
    provider_url = 'https://www.targetpay.com'

    def __init__(self, testing=False, rtlo=None):
        self.rtlo = (
            rtlo or
            getattr(settings, 'OSSO_PAYMENT_TARGETPAY', {}).get('rtlo'))
        self.test_mode = testing

    def get_start_url(self):
        return '{}/{}/start'.format(self.provider_url, self.provider_sub)

    def get_start_parameters(self):
        parameters = {
            'rtlo': self.rtlo,
            'description': self.payment.description,
            'amount': int(self.payment.amount * 100),
            'returnurl': self.build_absolute_uri(reverse(
                'osso_payment_targetpay_return',
                kwargs={'payment_id': self.payment.id})),
            'cancelurl': self.build_absolute_uri(reverse(
                'osso_payment_targetpay_abort',
                kwargs={'payment_id': self.payment.id})),
            'reporturl': self.build_absolute_uri(reverse(
                'osso_payment_targetpay_report',
                kwargs={'payment_id': self.payment.id})),
        }
        return parameters

    def get_check_url(self):
        return '{}/{}/check'.format(self.provider_url, self.provider_sub)

    def get_check_parameters(self, payment):
        parameters = {
            'rtlo': self.rtlo,
            'trxid': payment.unique_key.split('-', 1)[1],
            # > Als u voor once '1' invult dan zal slechts 1x een OK status
            # > teruggegeven worden.  Als de bovenstaande URL nog een keer
            # > wordt aangeroepen voor hetzelfde Transactie ID dan krijgt u
            # > een foutmelding 'TP00014 (Reeds ingewisseld)' terug.  Als u
            # > voor once '0' invult dan zal steeds een OK status terug
            # > blijven komen.
            'once': '0',  # no need, we use atomic db update
        }
        return parameters

    def get_payment_form(self, payment):
        """
        Return the verbatim HTML form that should be (auto)submitted by
        the user to go to the payment page.

        Use once only (because we set properties on this object).
        (A bit of a hack; it'd be better it we abstracted that away to
        another instance, but not right now.)
        """
        # Set payment locally for later use; less argument passing.
        assert not hasattr(self, 'payment'), self.payment
        self.payment = payment

        host_prefix = payment.realm
        if '://' not in host_prefix:
            host_prefix = 'http://%s' % (host_prefix,)
        self.build_absolute_uri = (lambda x: host_prefix + x)

        if payment.transfer_initiated:
            raise PaymentAlreadyUsed()  # user clicked back?

        payment_url = self.start_transaction()
        return self.create_html_form_from_url(payment_url, 'targetpay_form')

    def start_transaction(self):
        parameters = self.get_start_parameters()

        # https://www.targetpay.com/SUB/start?rtlo=$NUMBER&
        #   description=test123&amount=123&
        #   returnurl=https://$HOST/return&
        #   cancelurl=https://$HOST/cancel&
        #   reporturl=https://$HOST/report&test=1&ver=3
        ret = self._do_request(self.get_start_url(), parameters)
        # 000000 177XXX584|https://www.targetpay.com/SUB/launch?
        #   trxid=177XXX584&ec=779XXXXXXXXX273
        if ' ' in ret:
            status, rest = ret.split(' ', 1)
        else:
            assert status != '000000', ret

        if status != '000000':
            self.handle_error(self.payment, ret)
            assert False

        try:
            trxid, payment_url = rest.split('|', 1)
            if not payment_url.startswith('https:'):
                raise ValueError('no https?')
        except ValueError:
            self.handle_error(self.payment, ret)
            assert False

        # Initiate it and store the unique_key with our submethod as
        # first argument. (Does an atomic check.)
        self.payment.set_unique_key('{}-{}'.format(self.provider_sub, trxid))

        return payment_url

    def request_status(self, payment, request):
        """
        Check status at payment backend and store value locally.
        """
        parameters = self.get_check_parameters(payment)
        ret = self._do_request(self.get_check_url(), parameters)

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
            payment.set_blob('targetpay.{provider_sub}: {json_blob}'.format(
                provider_sub=self.provider_sub,
                json_blob=json.dumps(postdata)))
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

    def _do_request(self, url, parameters):
        url = '{url}?{parameters}'.format(
            url=url, parameters=urlencode(parameters))

        log(url, 'targetpay', 'qry.{}'.format(self.provider_sub))
        ret = http_get(url)
        log(ret, 'targetpay', 'ret.{}'.format(self.provider_sub))

        return ret


class TargetpayIdeal(TargetpayBase, Provider):
    # This should be an IdealProvider, not a Provider, but that's only
    # true once we implement get_banks(). However, things works fine by
    # letting Targetpay show the bank selection instead.
    provider_sub = 'ideal'

    def get_start_parameters(self):
        parameters = super(TargetpayIdeal, self).get_start_parameters()
        parameters['ver'] = '3'

        if self.test_mode:
            # > Om uw orderafhandeling te testen kunt u bij de start
            # > functie uit paragraaf 3 de parameter
            # > test=1 opgeven. Met deze instelling krijgt u altijd een
            # > '00000 OK' status terug wanneer u de check functie uit
            # > paragraaf 5 aanroept.
            # You'll return to the returnurl.
            parameters['test'] = '1'

        return parameters


class TargetpayMrCash(TargetpayBase, Provider):
    provider_sub = 'mrcash'
    language_codes = ('NL', 'FR', 'EN')  # limited valid languages

    def get_start_parameters(self):
        parameters = super(TargetpayMrCash, self).get_start_parameters()

        assert self.language_code in self.language_codes, self.language_code
        parameters['lang'] = self.language_code
        assert self.remote_addr, 'remote_addr is mandatory!'
        parameters['userip'] = self.remote_addr

        return parameters

    def get_check_parameters(self, payment):
        parameters = super(TargetpayMrCash, self).get_check_parameters(payment)

        if self.test_mode:
            # > Vul hier 1 in en de transactie wordt ook als OK
            # > aangemerkt als deze nog niet betaald is. Alle andere
            # > checks worden wel net als normaal doorlopen.
            parameters['test'] = '1'

        return parameters

    def get_payment_form(self, payment, locale=None, remote_addr=None):
        """
        Return the verbatim HTML form that should be (auto)submitted by
        the user to go to the payment page.

        Use once only (because we set properties on this object).
        (A bit of a hack; it'd be better it we abstracted that away to
        another instance, but not right now.)
        """
        locale = locale or 'nl_NL'
        assert len(locale.split('_')) == 2, locale  # looks like nl_NL ?
        self.language_code = locale.split('_')[0].upper()  # NL/FR/EN
        self.remote_addr = remote_addr or ''

        return super(TargetpayMrCash, self).get_payment_form(payment)
