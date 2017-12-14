# vim: set ts=8 sw=4 sts=4 et ai:
import unittest
from base64 import b64encode
from hashlib import sha256
from urllib2 import Request, urlopen

from osso.payment.base import IdealProvider
from osso.payment.conditional import reverse, settings
from osso.payment.xmlutils import dom2dictlist, string2dom, xmlescape
from osso.payment.signals import payment_updated


__all__ = ('Sofort', 'SofortIdealError')

# Continue-URL, use hash-pass so we can confirm that the transaction
# was started.  (Note that it is unsafe to assume you get your money.
# But the odds are probably high.)
# http://-USER_VARIABLE_0-/api/sofortideal/-USER_VARIABLE_1-/cont/-USER_VARIABLE_1_HASH_PASS-/
#
# Abort-URL, no hash-pass checks so reverse engineering the 'cont'
# password is harder.
# (?error_codes=1234,5678 will get added)
# http://-USER_VARIABLE_0-/api/sofortideal/-USER_VARIABLE_1-/abort/
#
# Delivery-report-URL, this will be done with POST-data and proper
# payment details.
# http://-USER_VARIABLE_0-/api/sofortideal/-USER_VARIABLE_1-/dlr/

# Sobald der Testmodus aktiviert ist, koennen Sie mit folgenden
# Betraegen verschiedene Statusmeldungen bei iDEAL provozieren:
# 1 EUR => Erfolgreiche Zahlung
# 2 EUR => Abbruch der Zahlung
# 4 EUR => Ausstehende Zahlung


class SofortIdealError(ValueError):
    """
    1000 Invalid request.
    1001 Technical error.
    6000 An unknown error occured.
    6001 Session expired.
    7007 Amount required.
    7008 Invalid amount.
    7009 Reason required.
    7010 Invalid sender country id.
    7011 Invalid recipient country id.
    7012 Invalid sender bank code.
    7013 Sender account equals recipient account.
    7014 Invalid hash.

    Example: error_codes=7012,7013,7014
    """
    pass


class Sofort(IdealProvider):
    OUT_REQUIRED = (
        'amount', 'reason_1', 'sender_bank_code', 'sender_country_id',
        'project_password'
    )  # + user_id, project_id, hash
    OUT_OPTIONAL = (
        'sender_holder', 'sender_account_number', 'reason_2',
        'user_variable_0', 'user_variable_1', 'user_variable_2',
        'user_variable_3', 'user_variable_4',
        'user_variable_5'
    )  # technically, project_password is not required..
    OUT_ORDER = (
        'user_id', 'project_id', 'sender_holder', 'sender_account_number',
        'sender_bank_code', 'sender_country_id', 'amount',
        'reason_1', 'reason_2', 'user_variable_0', 'user_variable_1',
        'user_variable_2', 'user_variable_3', 'user_variable_4',
        'user_variable_5', 'project_password'
    )
    IN_ORDER = (
        'transaction', 'user_id', 'project_id', 'sender_holder',
        'sender_account_number', 'sender_bank_name', 'sender_bank_bic',
        'sender_iban', 'sender_country_id', 'recipient_holder',
        'recipient_account_number', 'recipient_bank_code',
        'recipient_bank_name', 'recipient_bank_bic', 'recipient_iban',
        'recipient_country_id', 'amount', 'currency_id', 'reason_1',
        'reason_2', 'user_variable_0', 'user_variable_1',
        'user_variable_2', 'user_variable_3', 'user_variable_4',
        'user_variable_5', 'created', 'status', 'status_modified',
        'notification_password'
    )  # optional: amount_refunded, amount_refunded_integer

    def __init__(self, testing=False, user_id=None, project_id=None,
                 api_key=None, project_password=None):
        sofort_settings = (
            settings and getattr(settings, 'OSSO_PAYMENT_SOFORT', {}) or {})
        user_id = user_id or sofort_settings['user_id']
        project_id = project_id or sofort_settings['project_id']
        api_key = api_key or sofort_settings['api_key']
        project_password = (
            project_password or sofort_settings['project_password'])
        if (not user_id or not project_id or not api_key or
                not project_password):
            raise TypeError(
                "Required argument 'user_id', 'project_id', 'api_key' or "
                "'project_password' not found")

        self.testing = bool(testing)
        self.user_id = str(user_id)
        self.project_id = int(project_id)
        self.api_key = str(api_key)
        self.project_password = str(project_password)

    def get_banks(self, banks_url=None):
        # Implement a fake mode
        if self.testing:
            return [{'id': 31, 'name': 'ABN Amro'},
                    {'id': 91, 'name': 'Friesland Bank'}]

        banks_url = banks_url or 'https://www.sofort.com/payment/ideal/banks'
        data = self.sofort_request(banks_url, self.user_id, self.api_key)
        banks = banks2dictlist(data)
        return banks

    def get_payment_form(self, payment, bank_id):
        return self._get_form(
            amount=payment.get_amount(),
            reason_1=payment.description,
            sender_bank_code=bank_id,
            user_variable_0=payment.id,
            # This is a unique key with a bit of additional data to
            # avoid dictionary attacks against our shared secret.
            # (We'll have sofort hash this, instead of the payment.id.)
            user_variable_1=payment.get_unique_key()
        )

    def process_passed(self, payment, transaction_hash):
        """
        Check if the transaction_hash is valid and mark the payment as
        completed.

        The payment_updated signal is fired to notify the application
        of the payment success.
        """
        # Re-create hash and compare.
        project_password = (
            getattr(settings, 'OSSO_PAYMENT_SOFORT', {})
            .get('project_password', '').encode('utf-8'))
        calculated_hash = sha256('%s%s' % (
            payment.get_unique_key(),
            project_password
        )).hexdigest()
        if calculated_hash.lower() != str(transaction_hash).lower():
            raise ValueError(
                'Hash for transaction passed mismatch for payment %s' %
                (payment.id,))

        # This raises a ValueError if this is not possible
        payment.mark_passed()
        # XXX/FIXME: no mark_succeeded here??
        # Signal that something has happened
        payment_updated.send(sender=payment, change='passed')

    def process_aborted(self, payment, transaction_key):
        """
        Mark the payment as failed.

        The payment_updated signal is fired to notify the application
        of the payment failure.
        """
        # Check if the sent transaction key matches.
        if payment.get_unique_key().lower() != str(transaction_key).lower():
            raise ValueError(
                'Key for transaction aborted mismatch for payment %s' %
                (payment.id,))

        # This raises a ValueError if this is not possible.
        payment.mark_aborted()
        # Signal that something has happened.
        payment_updated.send(sender=payment, change='aborted')

    def _get_form_data(self, **kwargs):
        # Rather verbose check to see that we've got only arguments that
        # we want and no other.
        data = {}
        try:
            for key in self.OUT_REQUIRED:
                if key == 'sender_country_id':
                    data[key] = kwargs.pop(key, 'NL')
                elif key == 'project_password':
                    data[key] = kwargs.pop(key, self.project_password)
                elif key in ('reason_1', 'reason_2'):
                    value = kwargs.pop(key).encode('ascii', 'replace')
                    if any(i not in (
                            '0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZ'
                            'abcdefghijklmnopqrstuvwxyz +,-.') for i in value):
                        raise ValueError(
                            'Illegal character found in %s: %s' % (key, value))
                    if len(value) > 27:
                        raise ValueError(
                            'Size of %s too large (max 27): %s' % (key, value))
                    data[key] = value
                else:
                    data[key] = kwargs.pop(key)
        except KeyError:
            raise TypeError("Required argument '%s' not found" % (key,))
        for key in self.OUT_OPTIONAL:
            data[key] = kwargs.pop(key, '')
        if kwargs:
            raise TypeError(
                "'%s' is an invalid keyword argument for this function" %
                (kwargs.keys()[0],))

        # Set the other missing arguments and stringify all
        data['user_id'] = self.user_id
        data['project_id'] = self.project_id
        for key, value in data.items():
            data[key] = unicode(value).encode('utf-8')

        # Create hash over the arguments
        values = []
        for key in self.OUT_ORDER:
            values.append(data[key])
        data['hash'] = sha256('|'.join(values)).hexdigest()

        # Remove the secret
        del data['project_password']

        return data

    def _get_form(self, button_text=None, form_url=None, **kwargs):
        button_text = button_text or 'iDEAL'
        if not form_url:
            if self.testing:
                form_url = reverse(
                    'osso_payment_sofort_fake_ideal',
                    kwargs={'bank_code': kwargs['sender_bank_code']})
            else:
                form_url = 'https://www.sofort.com/payment/ideal'

        fields = []
        for key, value in self._get_form_data(**kwargs).items():
            fields.append(
                '<input type="hidden" name="%s" value="%s"/>' %
                (str(key), xmlescape(value, '"')))
        return (
            '<form method="post" action="%(url)s">%(fields)s'
            '<input type="submit" value="%(button_text)s"/></form>' % {
                'url': form_url,
                'button_text': button_text,
                'fields': ''.join(fields)
            })

    @classmethod
    def sofort_request(cls, url, user_id, api_key, headers=(),
                       postdata=None, extra_headers=()):
        """
        Example urls:
        https://api.sofort.com/api/xml
        https://www.sofort.com/payment/ideal/banks
         ^-- shall return a list of banks
        """
        if postdata is None:
            data = ''  # must use data or we get a GET request
        else:
            raise NotImplementedError('Should urlencode postdata into data..')

        request = Request(url)
        request.add_data(data)
        auth = b64encode(':'.join([user_id, api_key]))
        request.add_header(
            'Authorization', 'Basic %s' % (auth,))
        request.add_header(
            'Content-Type', 'application/xml; charset=UTF-8')
        request.add_header(
            'Accept', 'application/xml; charset=UTF-8')
        for key, value in extra_headers:
            request.add_header(key, value)

        response = urlopen(request)
        return response.read()

    @classmethod
    def validate_response(cls, data, notification_password=None):
        sofort_settings = (
            settings and getattr(settings, 'OSSO_PAYMENT_SOFORT', {}) or {})
        if 'notification_password' in data:
            raise TypeError(
                "'notification_password' is not supposed to be in data")
        if notification_password is None:
            if 'notification_password' in sofort_settings:
                notification_password = (
                    sofort_settings['notification_password'])
            else:
                raise TypeError(
                    "Required parameter 'notification_password' not found")
        if 'hash' not in data:
            raise TypeError("Required key 'hash' not found in argument 'data'")

        # Create hash over the arguments
        values = []
        for key in cls.IN_ORDER:
            values.append(unicode(data.get(key, '')).encode('utf-8'))
        values.append(unicode(notification_password).encode('utf-8'))
        calculated_hash = sha256('|'.join(values)).hexdigest().strip().lower()

        # Check hash
        received_hash = unicode(data['hash']).encode('utf-8').strip().lower()
        if received_hash != calculated_hash:
            raise SofortIdealError(7014, 'Invalid hash')


def banks2dictlist(xml):
    """
    Gets all /ideal/banks/bank elements as a list of dictionaries.
    (Don't try to be funny and add more banks elements. Only the first
    one will be scoured for bank elements.)

    Source: https://www.sofort.com/payment/ideal/banks

    We replace the 'code'/'name' pairs with 'id'/'name' and cast the ids
    to integers.
    """
    assert isinstance(xml, str), 'Pass me a binary string, not %r' % (xml,)
    dictlist = dom2dictlist(string2dom(xml), inside=('ideal', 'banks'))
    for dict in dictlist:
        assert dict['name']
        dict['id'] = int(dict['code'])
        del dict['code']
    return dictlist


class SofortTest(unittest.TestCase):
    def test_test(self):
        self.assertEqual(1, 1)

    def test_banks2dict(self):
        input = '''<?xml version="1.0" encoding="UTF-8"?>
        <ideal>
            <banks>
                <bank>
                    <code>31</code>
                    <name>ABN Amro</name>
                </bank>
                <bank>
                    <code>91</code>
                    <name>Friesland Bank</name>
                </bank>
            </banks>
        </ideal>
        '''
        expected = [
            {'id': 31, 'name': 'ABN Amro'},
            {'id': 91, 'name': 'Friesland Bank'},
        ]
        output = banks2dictlist(input)
        self.assertEqual(output, expected)

    def test_getform(self):
        ideal = Sofort(
            user_id=1, project_id=2, api_key=3,
            project_password='geheim')
        data = ideal._get_form(
            amount=12.34, reason_1=u'my-rEason',
            sender_bank_code=91)
        self.assertTrue(data.startswith('<form '))
        self.assertTrue('"12.34"' in data)
        # self.assertTrue('"my_r&#8364;ason"' in data)
        # ^-- this was before cleaning up the description
        self.assertTrue('"my-rEason"' in data)
        self.assertTrue(
            ('"88064715a88f79517612c2a7a082706d'
             '6fa1327a8c69890dfb74aec6d9678760"') in data)
        self.assertFalse('"geheim"' in data)
        self.assertTrue(data.endswith('</form>'))

    def test_validate_response(self):
        input = {
            'unused': 1, 'amount': 12.34, 'reason_1': u'my_r\u20acason',
            'sender_bank_code': 91,
            'hash': ('7004dd7f0ba4a3c679f5b9c4d97c129f'
                     'fe420eff0b70e2e6431b25afd02aab43'),
        }
        Sofort.validate_response(input, notification_password='geheim')


if __name__ == '__main__':
    unittest.main()
