# vim: set ts=8 sw=4 sts=4 et ai:
# Parts of this code taken directly from the
# "Python library for Mollie iDeal implementation"
# by Dave de Fijter - Indentity - http://www.indentity.nl
import ast
import ssl
import unittest
import urllib
import urllib2
import urlparse
from lxml import objectify

from osso.autolog.utils import log
from osso.payment import BuyerError, PaymentAlreadyUsed, PaymentSuspect
from osso.payment import ProviderError, ProviderBadConfig, ProviderDown
from osso.payment.ideal import BaseIdeal
from osso.payment.xmlutils import dom2dictlist, string2dom, xmlstrip

# conditional django includes
try:
    from django.conf import settings
except ImportError:
    settings = None
else:
    from django.core.urlresolvers import reverse
try:
    from osso.aboutconfig.utils import aboutconfig
except ImportError:
    aboutconfig = None


BANKS_MARCH_2012 = (
    "[{'id': 31, 'name': u'ABN AMRO'}, {'id': 761, 'name': u'ASN Bank'}, "
    "{'id': 91, 'name': u'Friesland Bank'}, {'id': 721, 'name': u'ING'}, "
    "{'id': 21, 'name': u'Rabobank'}, {'id': 771, 'name': u'RegioBank'}, "
    "{'id': 751, 'name': u'SNS Bank'}, {'id': 511, 'name': u'Triodos Bank'}, "
    "{'id': 161, 'name': u'van Lanschot'}]")
E_BANK_DOWN = -0x4321  # mollie uses negative index errors.. adding custom err


class Ideal(BaseIdeal):
    def __init__(self, testing=False, partner_id=None, profile_key=None,
                 api_url=None):
        mollie_settings = (
            settings and getattr(settings, 'OSSO_PAYMENT_MOLLIE', {}) or {})
        # Store args
        self.testing = bool(testing)
        self.partner_id = (
            partner_id or mollie_settings['partner_id'])
        self.profile_key = (
            profile_key or mollie_settings.get('profile_key', None))
        self.api_url = (
            api_url or mollie_settings.get(
                'api_url', 'https://secure.mollie.nl/xml/ideal'))

    def get_banks(self):
        params = {'a': 'banklist'}

        # We don't want to fail the bank showing just because there is a
        # temporary failure.
        try:
            response = self._do_request(params, timeout_seconds=1)
        except (ProviderError, urllib2.URLError, ssl.SSLError):
            # ProviderError can be "(-99, u'Service (temporary) unavailable')"
            if aboutconfig:
                banks = ast.literal_eval(
                    aboutconfig('payment.provider.mollie.banks',
                                BANKS_MARCH_2012))
            else:
                banks = ast.literal_eval(BANKS_MARCH_2012)
        else:
            banks = banks2dictlist(response)
            if aboutconfig:
                aboutconfig('payment.provider.mollie.banks',
                            repr(banks), set=True)

        return banks

    def get_payment_form(self, payment, bank_id):
        # Note that description should be clean. The caller should have
        # fed it through the provider specific clean_description().
        description = str(payment.description)
        if any(i not in ('0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZ'
                         'abcdefghijklmnopqrstuvwxyz +,-.')
               for i in description):
            raise BuyerError(
                'Illegal character found in description: %s' % (description,))
        if len(description) > 29:
            raise BuyerError(
                'Size of description too large (max 29): %s' % (description,))

        scheme_and_host = payment.realm
        if '://' in scheme_and_host:
            scheme, host = scheme_and_host.split('://', 1)
        else:
            scheme, host = 'http', scheme_and_host
        if host == 'localhost' or host.startswith('localhost:'):
            host = 'example.com'  # Mollie refuses 'localhost' even in testmode
        host_prefix = '%s://%s' % (scheme, host)

        # FIXME: namespace? osso_payment_mollie_ideal_report? :)
        report_url = '%s%s' % (
            host_prefix,
            reverse('mollie_ideal_report', kwargs={'payment_id': payment.id}))
        return_url = '%s%s' % (
            host_prefix,
            reverse('mollie_ideal_return', kwargs={'payment_id': payment.id}))

        # Check whether we've "used" this payment already. If we don't
        # check this here, we might first find out when setting
        # set_unique_key() below, and then we will have created a new
        # payment which we'll get status reports for. (And we won't
        # recognise those, since we won't know that it's the right key.)
        if payment.unique_key:
            raise PaymentAlreadyUsed()  # user clicked back?

        # Mollie takes the amount in cents.
        amount = int(payment.get_amount() * 100)

        params = {
            'a': 'fetch',
            'partnerid': self.partner_id,
            'amount': amount,
            'bank_id': '%04d' % (bank_id,),
            'description': description,
            'reporturl': report_url,
            'returnurl': return_url,
        }
        if self.profile_key:
            params['profile_key'] = self.profile_key

        response = self._do_request(params)
        try:
            order = order2dict(response)
        except ValueError:
            raise ProviderError('Provider response invalid', response)
        if order['currency'] != 'EUR':  # what else?
            raise ProviderError('Unexpected currency', response)
        if int(order['amount']) != amount:
            raise ProviderError(
                'Payment amount mismatch with request: %s vs. %s (cents)' %
                (order['amount'], amount), response)
        if len(order['transaction_id']) < 16:
            raise ProviderError(
                'Received transaction_id seems unsafe',
                order['transaction_id'])

        # Store transaction_id as the unique key. This happens to be a
        # 32 byte string. We add just a little bit of extra uniqueness
        # by appending our PK.
        if '-' in str(payment.id):
            raise NotImplementedError(  # rsplit below would fail
                'Cannot cope with minus in PK', payment.id)
        unique_key = '%s-%s' % (order['transaction_id'], payment.id)
        payment.set_unique_key(unique_key)

        # We have to split the URL into <input> boxes, or the form
        # method won't work.
        url, data = url2formdata(order['URL'])
        inputs = []
        for item in data:
            inputs.append('<input type="hidden" name="%s" value="%s"/>' % (
                (item[0].replace('&', '&amp;').replace('<', '&lt;')
                 .replace('>', '&gt;').replace('"', '&#34;')),
                (item[1].replace('&', '&amp;').replace('<', '&lt;')
                 .replace('>', '&gt;').replace('"', '&#34;')),
            ))

        # Must use GET, mollie doesn't like POST here.
        form = '<form id="ideal_form" method="GET" action="%s">%s</form>' % (
            (url.replace('&', '&amp;').replace('<', '&lt;')
             .replace('>', '&gt;').replace('"', '&#34;')),
            ''.join(inputs),
        )

        return form

    def process_report(self, payment, transaction_id):
        '''
        Check if the payment has succeeded. It queries the mollie
        interface and updates the payment status.

        The payment_updated signal is fired to notify the application
        of any success or failure.
        '''
        from osso.payment.signals import payment_updated

        # We stored the transaction_id in the unique_key. Get it from
        # payment.unique_key directly instead of using get_unique_key().
        # Otherwise we might be creating a bogus unique_key which we
        # won't be using.
        if str(payment.unique_key).rsplit('-', 1)[0] != str(transaction_id):
            raise PaymentSuspect(
                'Found transaction_id %s differing from payment %s' %
                (transaction_id, payment.id))
        if len(transaction_id) < 16:
            raise PaymentSuspect(
                'Found invalid transaction_id %s in payment %s' %
                (transaction_id, payment.id))
        if payment.is_success is not None:
            raise PaymentSuspect(
                'Got payment status report for %s which is already %s' %
                (payment.id, payment.is_success))

        # Continue and query Mollie for the payment status
        params = {
            'a': 'check',
            'partnerid': self.partner_id,
            'transaction_id': transaction_id,
        }
        response = self._do_request(params)
        domobj = objectify.fromstring(response)
        assert unicode(domobj.order.transaction_id) == unicode(transaction_id)
        assert int(domobj.order.amount) == int(payment.get_amount() * 100)
        assert unicode(domobj.order.currency) == 'EUR'

        # There is a bit of customer info in:
        #   order.consumer.consumerAccount,
        #   order.consumer.consumerName,
        #   order.consumer.consumerCity.
        # But we ignore that for now. Instead, we store the entire XML
        # result so we can redo things later.
        new_blob = xmlstrip(response)
        payment.set_blob(new_blob)

        # Get the actual payment status
        is_paid = bool(domobj.order.payed)  # sic!
        if is_paid:
            # Two state changes at once for Mollie
            payment.mark_passed()
            payment.mark_succeeded()
            # Signal that something has happened
            payment_updated.send(sender=payment, change='passed')
        else:
            # Set payment status to aborted
            payment.mark_aborted()
            # Signal that something has happened
            payment_updated.send(sender=payment, change='aborted')

    def _do_request(self, params, timeout_seconds=None):
        '''
        Do request, check for failure and return original XML as binary
        string.
        '''
        if self.testing:
            params['testmode'] = 'true'
        url = '%s?%s' % (self.api_url, urllib.urlencode(params))
        log(url, 'mollie', 'qry')
        response = urllib2.urlopen(url, data=None, timeout=timeout_seconds)
        data = response.read()
        log(data, 'mollie', 'ret')

        # Mollie implements error raising in more than one way. Find all
        # the available errors.
        errors = any2errorlist(data)
        if errors:
            # Translate some errors into something we can trap.
            for i in errors:
                # http://www.mollie.nl/support/documentatie/betaaldiensten/ideal/en/
                # (-2, u"A fetch was issued without specification "
                #      u"of 'partnerid'.")
                # (-2, u'This account does not exist or is suspended.')
                # ...
                if i[0] in (-2, -11, -13, -15, -16):
                    raise ProviderBadConfig(
                        ('Account does not exist or does not have enough '
                         'permissions'), data)
                # Our custom error from the <order>.
                # (E_BANK_DOWN, 'Your iDEAL-payment has not been setup '
                #               'because of a temporary technical error '
                #               'at the bank')
                if i[0] == E_BANK_DOWN:
                    try:
                        bank = int(params.get('bank_id'))
                        if aboutconfig:
                            banks = ast.literal_eval(
                                aboutconfig('payment.provider.mollie.banks',
                                            BANKS_MARCH_2012))
                            banks = dict((i['id'], i['name']) for i in banks)
                            bank = banks[bank]
                    except:
                        bank = '(unknown)'
                    raise ProviderDown('Mollie', bank)
            raise ProviderError(errors)

        return data


def any2errorlist(xml):
    '''
    Get either /item[@type="error"] elements, or an error inside some
    other element (using mollie's supercrappy <error>true</error> node.
    '''
    assert isinstance(xml, str), \
        'No, I\'m doing the decoding! Pass me a binary string.'
    errors = []
    dom = string2dom(xml)
    dictlist = dom2dictlist(dom, inside=('response',), li='item', strict=False)
    for item in dictlist:
        if 'errorcode' in item and item['errorcode'] != '0':
            errors.append(
                (int(item['errorcode']),
                 item.get('message', 'Error message missing')))
    dictlist = dom2dictlist(
        dom, inside=('response',), li='order', strict=False)
    if len(dictlist) == 1:
        if dictlist[0].get('error', '').strip().lower() == 'true':
            errors.append(
                (E_BANK_DOWN,
                 dictlist[0].get('message', 'Error message missing')))
    return errors


def banks2dictlist(xml):
    '''
    Gets all /response/bank elements as a list of dictionaries.

    We replace the 'bank_id'/'bank_name' pairs with 'id'/'name' and cast
    the ids to integers.
    '''
    assert isinstance(xml, str), \
        'No, I\'m doing the decoding! Pass me a binary string.'
    dictlist = dom2dictlist(string2dom(xml), inside=('response',), li='bank')
    for dict in dictlist:
        dict['name'] = dict['bank_name']
        del dict['bank_name']
        dict['id'] = int(dict['bank_id'])
        del dict['bank_id']
    return dictlist


def order2dict(xml):
    '''
    Reads the elements of the /response/order into a dictionary.
    '''
    assert isinstance(xml, str), \
        'No, I\'m doing the decoding! Pass me a binary string.'
    dictlist = dom2dictlist(string2dom(xml), inside=('response',), li='order')
    if len(dictlist) != 1:
        raise ValueError('Expected exactly one order item in %s' % (xml,))
    return dictlist[0]


def url2formdata(url):
    '''
    Split the URL into a scheme+netloc+path and split up query
    components.
    '''
    obj = urlparse.urlparse(url)
    items = tuple(urlparse.parse_qsl(obj.query))
    return '%s://%s%s' % (obj.scheme, obj.netloc, obj.path), items


class IdealTest(unittest.TestCase):
    def test_test(self):
        self.assertEqual(1, 1)

    def test_mollie_error_1(self):
        '''Mollie uses two types of errors: global'''
        input = '''<?xml version="1.0" ?>
        <response>
            <item type="error">
                <errorcode>-3</errorcode>
                <message>There is a problem with the 'reporturl' \
you have provided: The URL host must not be 'localhost': localhost</message>
            </item>
            <item type="error">
                <errorcode>-4</errorcode>
            </item>
        </response>'''
        expected = [
            (-3, "There is a problem with the 'reporturl' you have provided: \
The URL host must not be 'localhost': localhost"),
            (-4, 'Error message missing'),
        ]
        output = any2errorlist(input)
        self.assertEqual(output, expected)

    def test_mollie_error_2(self):
        '''Mollie uses two types of errors: in-order'''
        input = '''<?xml version="1.0" ?>
        <response>
            <order>
                <URL>https://www.mollie.nl/files/idealbankfailure.html</URL>
                <currency/>
                <amount/>
                <error>true</error>
                <message>Your iDEAL-payment has not been setup because of \
a temporary technical error at the bank</message>
                <transaction_id/>
            </order>
        </response>'''
        expected = [
            (E_BANK_DOWN, 'Your iDEAL-payment has not been setup because \
of a temporary technical error at the bank'),
        ]
        output = any2errorlist(input)
        self.assertEqual(output, expected)

    def test_banks2dict(self):
        input = '''<?xml version="1.0"?>
        <response>
            <bank>
                <bank_id>0031</bank_id>
                <bank_name>ABN AMRO</bank_name>
            </bank>
            <bank>
                <bank_id>0721</bank_id>
                <bank_name>Postbank</bank_name>
            </bank>
            <bank>
                <bank_id>0021</bank_id>
                <bank_name>Rabobank</bank_name>
            </bank>
            <message>This is the current list of banks and their ID's \
that currently support iDEAL-payments</message>
        </response>
        '''
        expected = [
            {'id': 31, 'name': 'ABN AMRO'},
            {'id': 721, 'name': 'Postbank'},
            {'id': 21, 'name': 'Rabobank'},
        ]
        output = banks2dictlist(input)
        self.assertEqual(output, expected)

    def test_order2dict(self):
        input = '''<?xml version="1.0" ?>
        <response>
            <order>
                <transaction_id>aaabbbcccdddeeefff00011122233344\
</transaction_id>
                <amount>995</amount>
                <currency>EUR</currency>
                <URL>http://www.mollie.nl/partners/ideal-test-bank?\
order_nr=M12345&amp;transaction_id=aaabbbcccdddeeefff00011122233344&amp;\
trxid=0123</URL>
                <message>Your iDEAL-payment has successfully been setup. \
Your customer should visit the given URL to make the payment</message>
            </order>
        </response>
        '''
        expected = {
            'transaction_id': 'aaabbbcccdddeeefff00011122233344',
            'amount': '995',
            'currency': 'EUR',
            'URL': ('http://www.mollie.nl/partners/ideal-test-bank?'
                    'order_nr=M12345&transaction_id='
                    'aaabbbcccdddeeefff00011122233344&trxid=0123'),
            'message': ('Your iDEAL-payment has successfully been setup. '
                        'Your customer should visit the given URL to make '
                        'the payment'),
        }
        output = order2dict(input)
        self.assertEqual(output, expected)

    def test_url2formdata(self):
        input = ('http://www.mollie.nl/partners/ideal-test-bank?'
                 'order_nr=M12345&transaction_id='
                 'aaabbbcccdddeeefff00011122233344&trxid=0123')
        expected = (
            'http://www.mollie.nl/partners/ideal-test-bank',
            (
                ('order_nr', 'M12345'),
                ('transaction_id', 'aaabbbcccdddeeefff00011122233344'),
                ('trxid', '0123'),
            )
        )
        output = url2formdata(input)
        self.assertEqual(output, expected)

    def test_instance(self):
        # DISABLED: because it does an RPC call which might be
        # burdensome on the remote server if executed too often.
        # ideal = Ideal(testing=True, partner_id=123)
        # expected = [
        #     {'id': 9999, 'name': 'TBM Bank'}
        # ]
        # banks = ideal.get_banks()
        # self.assertEqual(banks, expected)
        pass


def main():
    unittest.main()


if __name__ == '__main__':
    main()
