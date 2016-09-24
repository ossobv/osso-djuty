# vim: set ts=8 sw=4 sts=4 et ai tw=79:
import socket
import time
import urllib2
import urlparse

from hashlib import md5
from lxml import objectify
from django.core.mail import mail_admins

from osso.autolog.utils import log
from osso.payment import PaymentAlreadyUsed, ProviderError
from osso.payment.xmlutils import string2dom, xmlescape

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


class MultiSafepay(object):
    XML_PAYMENT_REQUEST = '''<?xml version="1.0" encoding="UTF-8"?>
    <redirecttransaction ua="%(ua)s">
        <merchant>
            <account>%(account)s</account>
            <site_id>%(site_id)s</site_id>
            <site_secure_code>%(site_secure_code)s</site_secure_code>
            <notification_url>%(notification_url)s</notification_url>
            <redirect_url>%(redirect_url)s</redirect_url>
            <cancel_url>%(cancel_url)s</cancel_url>
            <close_window>false</close_window>
        </merchant>
        <customer>
            <locale>%(locale_code)s</locale>
            <ipaddress>%(remote_addr)s</ipaddress>
            <forwardedip></forwardedip>
            <firstname></firstname>
            <lastname></lastname>
            <address1></address1>
            <address2></address2>
            <housenumber></housenumber>
            <zipcode></zipcode>
            <city></city>
            <country>%(country_code)s</country>
            <phone></phone>
            <email>%(email)s</email>
        </customer>
        <transaction>
            <id>%(transaction_id)s</id>
            <currency>EUR</currency>
            <amount>%(amount_cents)s</amount>
            <description>%(description)s</description>
            <var1></var1>
            <var2></var2>
            <var3></var3>
            <items></items>
            <manual>false</manual>
            <gateway></gateway>
            <daysactive></daysactive>
        </transaction>
        <signature>%(signature)s</signature>
    </redirecttransaction>'''

    XML_STATUS_REQUEST = '''<?xml version="1.0" encoding="UTF-8"?>
    <status ua="%(ua)s">
        <merchant>
            <account>%(account)s</account>
            <site_id>%(site_id)s</site_id>
            <site_secure_code>%(site_secure_code)s</site_secure_code>
        </merchant>
        <transaction>
            <id>%(transaction_id)s</id>
        </transaction>
    </status>'''

    def __init__(self, testing=False):
        self.ua = 'osso.payment.provider.msp-1alpha'

        if testing:
            self.api_url = 'https://testapi.multisafepay.com/ewx/'
        else:
            self.api_url = 'https://api.multisafepay.com/ewx/'

        if settings:
            self.account = settings.OSSO_PAYMENT_MSP['account']
            self.site_id = settings.OSSO_PAYMENT_MSP['site_id']
            self.site_secure_code = (
                settings.OSSO_PAYMENT_MSP['site_secure_code'])

    def get_signature(self, payment):
        amount_cents = str(int(payment.amount * 100))
        currency = 'EUR'
        transaction_id = str(payment.id)
        return md5(amount_cents + currency + str(self.account) +
                   str(self.site_id) + transaction_id).hexdigest()

    def get_payment_form(self, payment, locale=None, remote_addr=None):
        # Check whether we've "used" this payment already. We don't really need
        # this for MSP here, but in our current implementation, the user of the
        # payment API calls mark_submitted() (transfer_initiated=yes) on the
        # redirecting/form page. When called a second time, that will raise an
        # error.
        if payment.transfer_initiated:
            raise PaymentAlreadyUsed()  # user clicked back?

        # (1) Start transaction by messaging MultiSafepay directly.
        result = self.start_transaction(payment, locale=locale,
                                        remote_addr=remote_addr)
        # result = '''<?xml version="1.0" encoding="UTF-8"?>
        # <redirecttransaction result="ok">
        #     <transaction>
        #         <id>4039</id>
        #         <payment_url>https://pay.multisafepay.com/pay/?transaction=12345&amp;lang=nl_NL</payment_url>
        #     </transaction>
        # </redirecttransaction>'''
        # OR
        # result = '''<?xml version="1.0" encoding="UTF-8"?>
        # <redirecttransaction result="error">
        #     <error>
        #         <code>1006</code>
        #         <description>Invalid transaction ID</description>
        #     </error>
        #     <transaction><id>4326</id></transaction>
        # </redirecttransaction>'''

        # (2) Fetch URL from results.
        try:
            dom = string2dom(result)

            # FIXME: ugly code
            error = dom.getElementsByTagName('error')
            if error:
                code = error[0].getElementsByTagName('code')[0]
                code = u''.join(i.wholeText for i in code.childNodes)
                desc = error[0].getElementsByTagName('description')[0]
                desc = u''.join(i.wholeText for i in desc.childNodes)
                if code == '1006':  # Invalid transaction ID
                    # User clicked back and a used payment was attempted
                    # again, or it could simply be that the credentials are
                    # bad.
                    log('Credentials bad or payment already used',
                        'msp', 'err')
                    raise PaymentAlreadyUsed()  # user clicked back somehow?

            payment_url_node = dom.getElementsByTagName('payment_url')[0]
            payment_url = u''.join(
                i.wholeText for i in payment_url_node.childNodes)
        except PaymentAlreadyUsed:
            raise
        except:
            mail_admins('Error when parsing result', result)  # XXX/TEMP
            raise

        # (3) Send user to URL.
        # We have to split the URL into <input> boxes, or the form
        # method won't work.
        url, data = url2formdata(payment_url)
        inputs = []
        for item in data:
            inputs.append('<input type="hidden" name="%s" value="%s"/>' % (
                (item[0].replace('&', '&amp;').replace('<', '&lt;')
                 .replace('>', '&gt;').replace('"', '&#34;')),
                (item[1].replace('&', '&amp;').replace('<', '&lt;')
                 .replace('>', '&gt;').replace('"', '&#34;')),
            ))

        # Must use GET, we're fed a GET url after all.
        form = '''<form id="msp_form" method="GET" action="%s">%s</form>''' % (
            (url.replace('&', '&amp;').replace('<', '&lt;')
             .replace('>', '&gt;').replace('"', '&#34;')),
            ''.join(inputs),
        )

        return form

    def request_status(self, payment):
        from osso.payment.signals import payment_updated

        result = self.check_transaction(payment)

        # Example response:
        # result = '''<status result="ok">
        #     <ewallet>
        #         <id>2060867</id><status>initialized</status>
        #         <fastcheckout>NO</fastcheckout>
        #         <created>20121204215042</created><modified>20121204215042</modified>
        #     </ewallet>
        #     <customer>
        #         <amount>4495</amount><currency>EUR</currency><account/>
        #         <locale>nl_NL</locale><firstname/><lastname/>
        #         <address1/><address2/><housenumber/><zipcode/>
        #         <city/><state/><country>NL</country><countryname/>
        #         <phone1/><phone2/><email/>
        #     </customer>
        #     <customer-delivery/>
        #     <transaction>
        #         <id>4052</id><currency>EUR</currency><amount>4495</amount>
        #         <description>PFD4L 44 berichten a EUR..</description>
        #         <var1/><var2/><var3/>
        #         <items>PFD4L 44 berichten a EUR..</items>
        #     </transaction>
        #     <paymentdetails>
        #         <type>MASTERCARD</type><accountid/>
        #         <accountholdername>A</accountholdername><externaltransactionid/>
        #     </paymentdetails>
        # </status>'''

        # ewallet/status will contain one of:
        # - completed: succesvol voltooid
        # - initialized: aangemaakt, maar nog niet voltooid
        # - uncleared: aangemaakt, maar nog niet vrijgesteld (credit cards)
        # - void: geannuleerd
        # - declined: afgewezen
        # - refunded: terugbetaald
        # - expired: verlopen

        domobj = objectify.fromstring(result)

        if domobj.attrib['result'] != 'ok':
            raise ProviderError('MSP status result is not ok', result)

        status = domobj.ewallet.status

        # For the canceled status, we get no transaction id?
        # And since 2013-09-22 05:10, nor we get one for the 'expired' status.
        if status not in ('canceled', 'expired'):
            if str(domobj.transaction.id) != str(payment.id):
                raise ProviderError('Wrong/missing ID for payment %d' %
                                    (payment.id,), result)

        if status == 'completed':
            # MSP has a habit of sending the completed status even though it
            # already told us to poll for it earlier. That doesn't matter, as
            # long as we make sure to not count it a second time.
            if payment.is_success is not True:  # None or False
                # Only fire if we didn't (succesfully) complete already.
                try:
                    payment.mark_passed()
                    payment.mark_succeeded()
                except ValueError:
                    # We can get a race condition here. Whatever SQL isolation
                    # level is used, we can get in trouble. The in late 2012,
                    # the default postgresql backend in Django 1.3 does 'read
                    # committed' isolation by default. MySQL default seems to
                    # be 'repeatable read' which would be enabled in postgresql
                    # with the following statement:
                    #
                    #   set session characteristics as
                    #       transaction isolation level repeatable read;
                    #
                    # If said level is used, we wouldn't abort here if this
                    # code is ran simultaneously *but* we'd abort at COMMIT
                    # time instead with an integrity/serialization error.
                    #
                    # In either case, we'd have an error. In the first case, we
                    # can find out the reason though.
                    #
                    # Sleep a bit.
                    time.sleep(0.5)
                    # Reget the payment.
                    payment = payment.__class__.objects.get(pk=payment.pk)
                    # Check whether someone else beat us to it.
                    if payment.is_success is True:
                        # Ok, nothing to see here.
                        pass
                    else:
                        # Something else went wrong.
                        raise
                else:
                    # Notify some people!
                    payment_updated.send(sender=payment, change='passed')

        elif status == 'initialized':
            # This means absolutely nothing, or does it? I thought
            # Initialized means that someone clicked next on the
            # payment interface.
            # It does appear that initialized is called when a
            # transaction is reopened after it had been cancelled.
            # In that case this is the time to reopen the thing.
            if payment.is_success is False:
                payment.mark_reset()
                payment_updated.send(sender=payment, change='reset')

        elif status == 'uncleared':
            # Uncleared is that the payment was started but is on hold.
            # This might need more work in the future.
            pass

        elif status in ('void', 'declined', 'expired'):
            # Extra MSP magic. Even though they send void ("cancelled") or
            # declined ("rejected") they can create a new transaction with our
            # same transaction id. That means that we cannot store anything
            # here. They can still choose to complete a payment.
            # #DO_NOT_DO#payment.mark_aborted()
            # #DO_NOT_DO#payment_updated.send(sender=payment, change='aborted')
            pass

        elif status == 'canceled':
            # For canceled, the transaction will expire and not be resumable.
            # Finally one we *can* abort.
            if payment.is_success is not False:  # None or True
                # Technically, this could suffer from the same problem as the
                # race condition for the 'completed' status above. However,
                # that one gets triggered far more often than this one.
                payment.mark_aborted()
                payment_updated.send(sender=payment, change='aborted')

        else:
            # refunded?
            raise NotImplementedError('Status %s not implemented!' % (status,))

        payment.set_blob(result, overwrite=True)

    def start_transaction(self, payment, locale=None, remote_addr=None):
        '''Called by the code before redirecting the user to MSP.'''
        locale = locale or 'nl_NL'
        assert len(locale.split('_')) == 2, locale  # looks like nl_NL ?
        remote_addr = remote_addr or ''

        # FIXME: namespace?
        host_prefix = payment.realm
        if '://' not in host_prefix:
            host_prefix = 'http://%s' % (host_prefix,)

        notification_url = '%s%s' % (
            host_prefix,
            reverse('msp_report'))
        redirect_url = '%s%s' % (
            host_prefix,
            reverse('msp_return', kwargs={'payment_id': payment.id}))
        cancel_url = '%s%s' % (
            host_prefix,
            reverse('msp_abort', kwargs={'payment_id': payment.id}))

        # Prepare the data!
        template = self.XML_PAYMENT_REQUEST
        extra_kwargs = {
            'transaction_id': payment.id,
            'notification_url': notification_url,
            'redirect_url': redirect_url,
            'cancel_url': cancel_url,
            'locale_code': locale,                      # nl_NL
            'country_code': locale.split('_', 1)[1],    # NL
            'remote_addr': remote_addr,
            'email': xmlescape(payment.paying_user.email),
            'amount_cents': int(payment.amount * 100),
            'description': xmlescape(payment.description),
            'signature': self.get_signature(payment),
        }

        # Do the query!
        return self._do_request(template, extra_kwargs)

    def check_transaction(self, payment):
        '''Called on return from MSP to check with MSP what the status is.'''
        template = self.XML_STATUS_REQUEST
        extra_kwargs = {
            'transaction_id': payment.id,
        }

        # Do the query!
        return self._do_request(template, extra_kwargs)

    def _do_request(self, template, extra_kwargs):
        kwargs = {
            'ua': self.ua,
            'account': self.account,
            'site_id': self.site_id,
            'site_secure_code': self.site_secure_code,
        }
        kwargs.update(extra_kwargs)
        body = template % kwargs

        headers = {
            'Content-Type': 'text/xml; charset=UTF-8',
            'Accept': '*/*',
            'User-Agent': self.ua,
        }

        # Apparently we get SSL handshake timeouts after 1m52. That's too
        # long. Try and reduce that by adding a defaulttimeout. Only if that
        # works can be start adding a retry.
        # NOTE: http://hg.python.org/cpython/rev/3d9a86b8cc98/
        # NOTE: http://hg.python.org/cpython/rev/ce4916ca06dd/
        socket.setdefaulttimeout(20)

        timeout_seconds = 5
        request = urllib2.Request(self.api_url, data=body.encode('utf-8'),
                                  headers=headers)

        log(body, 'msp', 'out')
        try:
            response = urllib2.urlopen(request, timeout=timeout_seconds)
        except urllib2.HTTPError as e:
            # TEMP: this could use some tweaking
            contents = e.read()
            mail_admins('Incoming error to this XML',
                        body + '\n\n--\n' + contents + '\n\nURL: ' +
                        self.api_url + '\n')
            log('Got error %s with response: %s' % (e.code, contents),
                'msp', 'error')
            raise
        except Exception as e:
            # TEMP: this could use some tweaking
            mail_admins('Incoming error to this XML', body + '\n\nURL: ' +
                        self.api_url + '\n')
            log('Got error: %s' % (e,), 'msp', 'error')
            raise
        else:
            data = response.read()
            log(data, 'msp', 'in')

        return data


def url2formdata(url):
    '''
    Split the URL into a scheme+netloc+path and split up query
    components.

    FIXME: duplicate code, also found in ideal..
    '''
    obj = urlparse.urlparse(url)
    items = tuple(urlparse.parse_qsl(obj.query))
    return '%s://%s%s' % (obj.scheme, obj.netloc, obj.path), items
