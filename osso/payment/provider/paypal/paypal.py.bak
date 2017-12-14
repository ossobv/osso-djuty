# vim: set ts=8 sw=4 sts=4 et ai:
import decimal
import unittest
import urllib
import urllib2
import urlparse

from osso.payment import (
    BuyerError, PaymentAlreadyUsed, PaymentSuspect, TryDifferentPayment,
    ProviderError, ProviderBadConfig, ProviderDown)
from osso.payment.base import Provider
from osso.payment.conditional import log, mail_admins, reverse, settings
from osso.payment.signals import payment_updated
from osso.payment.xmlutils import htmlesc


class Paypal(Provider):
    """
    Implementing the PayPal express checkout.

    https://www.x.com/developers/paypal/products/express-checkout
    https://www.x.com/developers/paypal/documentation-tools/quick-start-guides/express-checkout-api
    https://www.x.com/developers/paypal/documentation-tools/api/setexpresscheckout-api-operation-nvp
    https://www.x.com/developers/paypal/documentation-tools/api/doexpresscheckoutpayment-api-operation-nvp
    """
    def __init__(self, testing=False, username=None, password=None,
                 signature=None):
        paypal_settings = (
            settings and getattr(settings, 'OSSO_PAYMENT_PAYPAL', {}) or {})
        # Store args
        self.testing = bool(testing)
        self.username = username or paypal_settings['username']
        self.password = password or paypal_settings['password']
        self.signature = signature or paypal_settings['signature']
        # API urls
        # https://cms.paypal.com/us/cgi-bin?cmd=_render-content&content_ID=developer/howto_api_endpoints
        if self.testing:
            self.frontend_url = 'https://www.sandbox.paypal.com/webscr'
            self.backend_url = 'https://api-3t.sandbox.paypal.com/nvp'  # POST
        else:
            self.frontend_url = 'https://www.paypal.com/webscr'
            self.backend_url = 'https://api-3t.paypal.com/nvp'  # POST-api

    def get_payment_form(self, payment):
        # Note that description should be clean.
        # FIXME: the description is limited to 128 bytes alnum or
        # something similar? Not relevant for now, but we should check
        # that we're not feeding paypal something invalid...

        host_prefix = payment.realm
        if '://' not in host_prefix:
            host_prefix = 'http://%s' % (host_prefix,)

        success_url = '%s%s' % (host_prefix, reverse(
            'osso_payment_paypal_passed', kwargs={'payment_id': payment.id}))
        abort_url = '%s%s' % (host_prefix, reverse(
            'osso_payment_paypal_aborted', kwargs={'payment_id': payment.id}))

        # Check whether we've "used" this payment already. If we don't
        # check this here, we might first find out when setting
        # set_unique_key() below, and then we will have created a new
        # payment which we'll get status reports for. (And we won't
        # recognise those, since we won't know that it's the right key.)
        # FIXME/TODO: is it possible to not raise an error but continue
        # instead??
        if payment.unique_key:
            raise PaymentAlreadyUsed()  # user clicked back?

        # For some obscure reason, the payment total does not show up on
        # the initial SetExpressCheckout page shown by PayPal. We don't
        # need to show any other pages to the user, but we alter the
        # description to include the price.
        description_and_price = '%s - EUR %.2f' % (
            payment.description, payment.get_amount())
        params = {
            # API options
            'METHOD': 'SetExpressCheckout',
            'returnUrl': success_url,
            'cancelUrl': abort_url,
            # Mandatory payment info
            'PAYMENTREQUEST_0_AMT': '%.2f' % (payment.get_amount(),),
            'PAYMENTREQUEST_0_CURRENCYCODE': 'EUR',  # we're in the EU..
            'PAYMENTREQUEST_0_DESC': description_and_price,
            # UI options
            'BRANDNAME': payment.realm,
            # TODO: should be optional
            'LOCALECODE': 'NL',
            # Favor non-Paypal (creditcard) payments in UI.
            'LANDINGPAGE': 'Billing',
            # We don't need a PayPal account ("PayPal account optional").
            'SOLUTIONTYPE': 'Sole',
            # Disable shipping and useless notes. With shipping
            # disabled, we can skip the GetExpressCheckoutDetails and
            # jump right to the DoExpressCheckoutPayment
            'REQCONFIRMSHIPPING': '0',
            'NOSHIPPING': '1',
            'ALLOWNOTE': '0',
        }

        # Do request
        response = self._do_request(params)

        # SetExpressCheckout returns something like:
        #   TOKEN=EC%2d7V703271YD3213158&TIMESTAMP=2012%2d03%2d24T21%3a55%3a03Z
        #    &CORRELATIONID=35a823921598f&ACK=Success&VERSION=78&BUILD=2649250
        token = response['TOKEN']
        if len(token) < 16:
            raise BuyerError('Received TOKEN seems unsafe', token)

        # Store the TOKEN which, along with our PK, makes for a unique
        # key which is random enough not to attract any evil-doers. Not
        # that they would get very far anyway. The payment is performed
        # and validated by a call from us to paypal in process_passed().
        if '-' in str(payment.id):
            raise NotImplementedError(  # rsplit below would fail
                'Cannot cope with minus in PK', payment.id)
        unique_key = '%s-%s' % (token, str(payment.id).upper())
        payment.set_unique_key(unique_key)

        # Create a GET URL where the user gets redirected to:
        form = (
            '<form id="paypal_form" method="GET" action="%(action)s">'
            '<input type="hidden" name="cmd" value="_express-checkout"/>'
            '<input type="hidden" name="token" value="%(token)s"/>'
            '</form>'
        ) % {
            'action': htmlesc(self.frontend_url),
            'token': htmlesc(token),
        }
        return form

    def process_passed(self, payment, token, payer_id):
        """
        At this point we do not have the payment, but we're allowed to
        initiate it.
        """
        # We stored the token in the unique_key. Get it from
        # payment.unique_key directly instead of using get_unique_key().
        # Otherwise we might be creating a bogus unique_key which we
        # won't be using.
        if str(payment.unique_key).rsplit('-', 1)[0] != str(token):
            raise PaymentSuspect(
                'Found token %s differing from payment %s' %
                (token, payment.id))
        if len(token) < 16:
            raise PaymentSuspect(
                'Found invalid token %s in payment %s' %
                (token, payment.id))
        if payment.is_success is not None:
            raise PaymentSuspect(
                'Got payment status report for %s which is already %s' %
                (payment.id, payment.is_success))

        # Continue and poke Paypal to make the payment.
        # We do have the option to call GetExpressCheckoutDetails first
        # to see what the user-provided parameters are. But, we don't
        # care about any of those. Just give us the money.
        params = {
            # API options
            'METHOD': 'DoExpressCheckoutPayment',
            # Mandatory payment info
            'PAYMENTREQUEST_0_AMT': '%.2f' % (payment.get_amount(),),
            'PAYMENTREQUEST_0_CURRENCYCODE': 'EUR',  # we're in the EU..
            # Mandatory verification info
            'TOKEN': token,
            'PAYERID': payer_id,
            # Optional notification URL (IPN): we may implement this
            # later, but I believe we need to have HTTPS enabled for
            # this to work on live.
            # 'PAYMENTREQUEST_0_NOTIFYURL: 'http://example.com/notify.html',
        }

        # Do request
        response = self._do_request(params)

        # DoExpressCheckoutPayment returns something like:
        #   TOKEN=EC%2d3EM7309999999999T&SUCCESSPAGEREDIRECTREQUESTED=true
        #     &TIMESTAMP=2012%2d03%2d24T23%3a08%3a10Z&CORRELATIONID=abcdef1234567
        #     &ACK=Success&VERSION=78&BUILD=2649250&INSURANCEOPTIONSELECTED=false
        #     &SHIPPINGOPTIONISDEFAULT=false
        #     &PAYMENTINFO_0_TRANSACTIONID=11U999999E777777D
        #     &PAYMENTINFO_0_RECEIPTID=1111%2d2222%2d3333%2d4444
        #     &PAYMENTINFO_0_TRANSACTIONTYPE=expresscheckout
        #     &PAYMENTINFO_0_PAYMENTTYPE=instant
        #     &PAYMENTINFO_0_ORDERTIME=2012%2d03%2d24T23%3a08%3a07Z
        #     &PAYMENTINFO_0_AMT=10%2e00&PAYMENTINFO_0_FEEAMT=0%2e69
        #     &PAYMENTINFO_0_TAXAMT=0%2e00&PAYMENTINFO_0_CURRENCYCODE=EUR
        #     &PAYMENTINFO_0_PAYMENTSTATUS=Completed
        #     &PAYMENTINFO_0_PENDINGREASON=None&PAYMENTINFO_0_REASONCODE=None
        #     &PAYMENTINFO_0_PROTECTIONELIGIBILITY=Ineligible
        #     &PAYMENTINFO_0_PROTECTIONELIGIBILITYTYPE=None
        #     &PAYMENTINFO_0_SECUREMERCHANTACCOUNTID=ABC123XYZZZZZ
        #     &PAYMENTINFO_0_ERRORCODE=0&PAYMENTINFO_0_ACK=Success
        # There is lots of nice info in there. We store all of it for
        # later viewing in the blob.
        payment.set_blob('paypal: ' + repr(response))

        # Get the actual payment status
        is_paid = (response['PAYMENTINFO_0_ACK'] == 'Success')
        if is_paid:
            # Payment went well
            payment.mark_passed()
            # This, is a bit of a question mark though. At the moment,
            # there is no way for us to get more status if the deal
            # wasn't really sealed. We add some logging and hope for
            # the best.
            if (response['PAYMENTINFO_0_PAYMENTTYPE'] != 'instant' or
                    (decimal.Decimal(response['PAYMENTINFO_0_AMT']) !=
                        payment.get_amount()) or
                    response['PAYMENTINFO_0_PAYMENTSTATUS'] != 'Completed'):
                if mail_admins:
                    mail_admins(
                        ('Paypal payment %s not completed fully?' %
                         (payment.id,)),
                        repr(response)
                    )
            # Set payment status to succeeded
            payment.mark_succeeded()
            # Signal that something has happened
            payment_updated.send(sender=payment, change='passed')

        else:
            # This, is also a bit of a question mark. This is not
            # supposed to fail... will it autocorrect itself?
            if mail_admins:
                mail_admins(
                    ('Paypal payment %s not completed fully? (2)' %
                     (payment.id,)),
                    repr(response)
                )
            # Set payment status to aborted
            payment.mark_aborted()
            # Signal that something has happened
            payment_updated.send(sender=payment, change='aborted')

    def process_aborted(self, payment, token):
        # We stored the token in the unique_key. Get it from
        # payment.unique_key directly instead of using get_unique_key().
        # Otherwise we might be creating a bogus unique_key which we
        # won't be using.
        if str(payment.unique_key).rsplit('-', 1)[0] != str(token):
            raise BuyerError(
                'Found token %s differing from payment %s' %
                (token, payment.id))
        if len(token) < 16:
            raise BuyerError(
                'Found invalid token %s in payment %s' %
                (token, payment.id))
        if payment.is_success is not None:
            raise BuyerError(
                'Got payment status report for %s which is already %s' %
                (payment.id, payment.is_success))

        # This raises a ValueError if this is not possible.
        payment.mark_aborted()
        # Signal that something has happened.
        payment_updated.send(sender=payment, change='aborted')

    def _do_request(self, params):
        """
        Do request, check for failure and return original XML as binary
        string.
        """
        params['USER'] = self.username
        params['PWD'] = self.password
        params['SIGNATURE'] = self.signature
        params['VERSION'] = '78'  # not sure if needed

        urlencoded_params = urllib.urlencode(params)
        log(self.backend_url + '?' + urlencoded_params, 'paypal', 'qry')
        response = urllib2.urlopen(self.backend_url, urlencoded_params)
        data = response.read()
        log(data, 'paypal', 'ret')
        decoded = urlparse.parse_qs(data)

        ack = decoded.get('ACK', ['Failure'])[0]
        if ack != 'Success':
            # API failure codes:
            # https://cms.paypal.com/us/cgi-bin/?cmd=_render-content&content_ID=developer/e_howto_api_nvp_errorcodes
            errorcode = int(
                decoded.get('L_ERRORCODE0', ['-1'])[0])
            severity = decoded.get(
                'L_SEVERITYCODE0', ['Unspecified'])[0]
            shortmsg = decoded.get(
                'L_SHORTMESSAGE0', ['Unknown'])[0]
            longmsg = decoded.get(
                'L_LONGMESSAGE0', ['An unknown error occurred'])[0]
            if errorcode == 10001:
                # Internal Error
                raise ProviderDown('PayPal')
            if errorcode == 10002:
                # Error, Security Error, Security header is not valid
                raise ProviderBadConfig(
                    'Security error (paypal error 10002); '
                    'common cause is bad or test mode credentials')
            if errorcode == 10417:
                # Transaction cannot complete (Instruct the customer to
                # use an alternative payment method)
                raise TryDifferentPayment()
            raise ProviderError(errorcode, severity, shortmsg, longmsg)

        try:
            values = listdict2stringdict(decoded)
        except ValueError:
            raise ProviderError(repr(decoded))

        return values


def listdict2stringdict(listdict):
    """
    Convert a dictionary of lists into a dictionary of strings. Raises a
    ValueError if a list with multiple values is found.
    """
    ret = {}
    for key, value in listdict.items():
        if len(value) > 1:
            raise ValueError('Unexpected list of more than 1 item', value)
        ret[key] = ''.join(value)
    return ret


class PaypalTest(unittest.TestCase):
    def test_test(self):
        self.assertEqual(1, 1)

    def test_listdict2stringdict_1(self):
        input = {'abc': [], 'def': ['def'], 'ghi': [], 'jkl': ['jkl']}
        expected = {'abc': '', 'def': 'def', 'ghi': '', 'jkl': 'jkl'}
        self.assertEqual(listdict2stringdict(input), expected)

    def test_listdict2stringdict_2(self):
        input = {'abc': [], 'def': ['def', 'ghi'], 'ghi': [], 'jkl': ['jkl']}
        self.assertRaises(ValueError, listdict2stringdict, input)


if __name__ == '__main__':
    unittest.main()
