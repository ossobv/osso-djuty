# vim: set ts=8 sw=4 sts=4 et ai:
from base64 import b64encode

from osso.payment.conditional import settings


# XXX: this file is incomplete, unused and untested

"""
5000 Transaction ID missing.
5001 Amount missing.
5002 Transaction could not be found.
5003 Amount must not exceed transaction amount.
5004 Transaction has not been received yet.
5005 Transaction is marked as test transaction and cannot be marked as
     cancelled.
5006 No refund elements provided.
5007 Consumer Protection not closed.
5008 Product not supported.
5009 The Transaction could not be inserted due to an internal error.
5010 Invalid bank code.
5011 Invalid account number.
5018 Invalid BIC.
5019 Invalid IBAN.
5020 Invalid holder.
5021 Refunding of test and real transactions must not be mixed.
5018 Invalid BIC.
5019 Invalid IBAN.
5020 Invalid holder.
5021 Refunding of test and real transactions must not be mixed.
5022 Transaction isn't a EUR transaction. Only EUR transactions may be
     refunded.
5023 Sender-Block contains a real account and the records are test
     transactions. Real sender account and test transactions must not be
     mixed.
5024 Sender-Block contains a test account and the records are real
     transactions. Test sender account and real transactons must not be
     mixed.
5025 No sender for this transaction. Transaction has no account holder.
5026 Reason validation failed. Invalid reason.
"""


class Sofort(object):
    URL = 'https://api.sofort.com/api/xml'

    def __init__(self, user_id=None, project_id=None, api_key=None):
        sofort_settings = settings and getattr(
            settings, 'OSSO_PAYMENT_SOFORT', {}) or {}
        user_id = user_id or sofort_settings['user_id']
        project_id = project_id or sofort_settings['project_id']
        api_key = api_key or sofort_settings['api_key']
        if not user_id or not project_id or not api_key:
            raise TypeError('Need user_id, project_id and api_key')

        self.user_id = str(user_id)
        self.project_id = int(project_id)
        self.api_key = str(api_key)

    def get_headers(self):
        auth = b64encode(':'.join([self.user_id, self.api_key]))
        return (
            ('Authorization', 'Basic %s' % (auth,)),
            ('Content-Type', 'application/xml; charset=UTF-8'),
            ('Accept', 'application/xml; charset=UTF-8'),
        )


class SofortCall(object):
    """
    Abstract call
    """
    def __init__(self, sofort):
        self.sofort = sofort


class SofortMultipay(SofortCall):
    """
    <multipay>
        <project_id>123</project_id>
        <interface_version>osso-djuty-payment-sofort 0</interface_version>
        <user_variables>
            <!-- kan hier tot 20 items.. store hier de transid? -->
            <user_variable>1</user_variable>
        </user_variables>
        <amount>12.34</amount>
        <currency_code>EUR</currency_code>
        <reasons>
            <reason>Omschrijving</reason>
        </reasons>

        <success_url>http://www.test.de</success_url>
        <abort_url>http://www.direct-ebanking.com/test/test2.php</abort_url>a
        ...
        ...
        ...
    """
    pass


if __name__ == '__main__':
    pass
