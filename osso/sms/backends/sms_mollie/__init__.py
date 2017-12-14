# vim: set ts=8 sw=4 sts=4 et ai:
# See documentation at:
# * http://www.mollie.nl/support/documentatie/sms-diensten/keyword/mo/
# * http://www.mollie.nl/support/documentatie/sms-diensten/sms/http/?s=premium
# * http://www.mollie.nl/support/documentatie/sms-diensten/dlr/
# (parts taken from m3r consultancy mollie-python-1.0.0 example by Ivo
# van der Wijk)
import urllib.request, urllib.parse, urllib.error
import urllib.request, urllib.error, urllib.parse
import time
from xml.dom.minidom import parseString

from django.core.mail import mail_admins
from osso.aboutconfig.utils import aboutconfig
from osso.sms import BaseSmsBackend
from osso.sms.utils import sms_bodies_needed, sms_split

try:
    from osso.autolog.utils import log
except ImportError:
    log = lambda *x, **y: None


GATEWAY_CHOICES = (
    (2, 'Basic'),
    (4, 'Business'),
    (1, 'Business+'),
    (8, 'Landline'),
)

SMSTYPE_CHOICES = ('normal', 'wappush', 'vcard', 'flash', 'binary', 'long')

TARIFF_CHOICES = (0, 25, 40, 55, 60, 70, 80, 90, 110, 150, 200)

URL_CHOICES = (
    'https://api.messagebird.com/xml/sms',
)


class MollieSmsBackend(BaseSmsBackend):
    def __init__(self, *args, **kwargs):
        super(MollieSmsBackend, self).__init__(*args, **kwargs)
        self.url = aboutconfig('sms.backends.sms_mollie.url',
                               URL_CHOICES[0]).encode('utf-8')
        self.default_args = default_args = {}
        default_args['username'] = \
            aboutconfig('sms.backends.sms_mollie.username').encode('utf-8')
        default_args['md5_password'] = \
            aboutconfig('sms.backends.sms_mollie.md5pass').encode('utf-8')
        default_args['gateway'] = \
            aboutconfig('sms.backends.sms_mollie.gateway', '2').encode('utf-8')
        default_args['charset'] = 'UTF-8'
        default_args['type'] = 'normal'  # SMSTYPE_CHOICES
        default_args['replace_illegal_chars'] = 'true'

        # If dlrurl is set, we feed it to mollie. If it's not set, we
        # use the default as set through the mollie interface.
        delivery_report_url = \
            aboutconfig('sms.backends.sms_mollie.dlrurl', '').encode('utf-8')
        if delivery_report_url != '':
            default_args['dlrurl'] = delivery_report_url
            # or 'http://...' + reverse('sms_delivery_report')

    def send_messages(self, sms_messages, reply_to=None,
                      shortcode_keyword=None, tariff_cent=None):
        sent = 0
        for message in sms_messages:
            if self.send_sms(message, reply_to=reply_to,
                             shortcode_keyword=shortcode_keyword,
                             tariff_cent=tariff_cent):
                sent += 1
        return sent

    def send_sms(self, message, reply_to=None, shortcode_keyword=None,
                 tariff_cent=None):
        '''
        Use the mollie gateway to send out a message. The only
        difference between "premium" and "regular" sms is really
        whether we can charge the user or not. So the tariff_cent
        decides which type we'll use.

        For all premium sms, we must add a couple of parameters:
        tariff, (member), shortcode, keyword, (mid).

        For non-subscription premium sms we must add the Mollie mid
        parameter to replies. This is stored as mollie_id in the meta
        dictionary of the reply_to message. If the original message
        consists of multiple messages (is larger than 160 chars) it has
        multiple mollie_ids. This function will use them in a round-
        robin fashion.

        For subscription premium sms we do not have a reply_to message,
        so we use the shortcode_keyword parameter instead.
        '''
        is_premium = tariff_cent is not None
        append_meta = None

        # == HACK ==
        # Mollie's gateway 2 (the cheap one) does not deliver free
        # SMS to Vodafone reliably
        if (message.remote_operator and
                message.remote_operator.entire_code() == '204-04'):
            gateway = 1
        else:
            gateway = None
        # == END HACK ==

        # A regular message
        if not is_premium:
            new_status, body_count = self._send_regular(
                message=message.body,
                recipient_list=[message.remote_address],
                local_address=message.local_address,
                reference=message.id,
                gateway=gateway
            )

        # If this is a premium message, we need a couple of extra parameters
        elif is_premium:
            # Attempt to match the tariff to the available choices:
            # select one of the TARIFF_CHOICES, rounding upwards if
            # there is no exact match.
            tariff_cent = int(tariff_cent)
            tariff_cent = ([j for i, j in enumerate(TARIFF_CHOICES)
                            if ((-1,) + TARIFF_CHOICES)[i] < tariff_cent
                                                           <= j] or  # noqa
                           [TARIFF_CHOICES[-1]])[0]

            # Get shortcode and keyword from shortcode_keyword parameter
            # or from the reply_to.local_address.
            shortcode_keyword = (shortcode_keyword or
                                 (reply_to and reply_to.local_address))
            if shortcode_keyword is not None:
                if ' ' in shortcode_keyword:
                    shortcode, keyword = shortcode_keyword.split(' ', 1)
                else:
                    shortcode, keyword = shortcode_keyword, ''
            # Nothing? Attempt to use the message local address. Note
            # that this and the subsequent keyword setting only work
            # when certain conditions are met: local_address being the
            # shortcode and you own the 'ONBEKEND' keyword on that
            # shortcode.
            else:
                shortcode, keyword = message.local_address.split(' ', 1)[0], ''
            # No keyword? Use the Mollie catch-all keyword.
            if keyword == '':
                keyword = 'ONBEKEND'

            # It is either a reply or a subscription message.
            if reply_to is not None:
                subscribed = False
                needed = sms_bodies_needed(len(message.body))
                mollie_id = _get_next_mollie_id(reply_to, needed)
                if mollie_id is not None:
                    append_meta = {'mollie_id': mollie_id}
            else:
                subscribed = True
                mollie_id = None

            new_status, body_count = self._send_premium(
                message=message.body,
                recipient_list=[message.remote_address],
                local_address=message.local_address,
                reference=message.id,
                gateway=gateway,
                mollie_id=mollie_id,
                tariff_cent=tariff_cent,
                member=subscribed,
                shortcode=shortcode,
                keyword=keyword
            )

        # This is possible.. for now..
        # Because mollie has so many problems, we'll rather have to mark
        # resilient real failures as bad by hand, than having to redo
        # many messages when the gateway is down for a minute or 10 (or
        # more).
        if new_status == 'retry':
            return False

        # Set status and optional metadata, and save.
        message.status = new_status
        message.body_count = body_count
        message.meta_append(append_meta, commit=False)
        message.save()
        return new_status == 'pnd'

    def _send_regular(self, message, recipient_list, local_address,
                      reference=None, gateway=None):
        args = self.default_args.copy()
        args['recipients'] = ','.join(recipient_list).encode('utf-8')
        args['originator'] = local_address.encode('utf-8')
        if reference is not None:
            args['reference'] = str(reference).encode('utf-8')
        if gateway is not None:
            args['gateway'] = str(gateway).encode('utf-8')

        return self._send(message, args)

    def _send_premium(self, message, recipient_list, local_address,
                      reference=None, gateway=None, mollie_id=None,
                      tariff_cent=0, member=False,
                      shortcode=None, keyword=None):
        args = self.default_args.copy()
        args['recipients'] = ','.join(recipient_list).encode('utf-8')
        args['originator'] = local_address.encode('utf-8')
        if reference is not None:
            args['reference'] = str(reference).encode('utf-8')
        if gateway is not None:
            args['gateway'] = str(gateway).encode('utf-8')
        if mollie_id is not None:
            args['mid'] = str(mollie_id).encode('utf-8')

        args['tariff'] = '%03d' % tariff_cent  # three-char tariff
        args['member'] = ('false', 'true')[bool(member)]

        if shortcode is not None:
            args['shortcode'] = str(shortcode).encode('utf-8')
        if keyword is not None:
            args['keyword'] = str(keyword).encode('utf-8')

        return self._send(message, args)

    def _send(self, message, args):
        '''
        Returns a tuple with the text message status and the number of
        text message bodies needed.
        '''
        args = args.copy()

        # Check message length
        # """Via de API is het mogelijk maximaal 1377 tekens per bericht te
        # gebruiken. Het bericht wordt opgesplitst in delen van 153 tekens, in
        # maximaal 9 SMS-berichten. (9x 153 tekens).
        # Let op! U betaalt per verzonden SMS-bericht. Bij een bericht met 300
        # tekens worden 2 SMS-berichten verstuurd."""
        # """message: maximaal 160 tekens (tenzij long sms of binary)"""
        #
        # In geval binary, doe je N chars UDH in HEX en de overige chars
        # van het bericht in cp1252 (charset="Windows-1252"). Bedenk dat
        # 6 chars UDH ceil(6*8/7) chars opmaken, vandaar dat er nog 153
        # chars over zijn per long sms part. Meer info in gsmencoding.py
        # en op http://en.wikipedia.org/wiki/Concatenated_SMS
        #
        # NOTE: Checking the length of the message without considering
        # the 7-bit GSM charset + extensions is wrong. However, either
        # the sms_split() function or the replace_illegal_chars argument
        # should ensure that the messages stay within bounds.
        if len(message) <= 160:
            message_parts = [(message, args['reference'])]
            body_count = 1
        elif (args.get('tariff', '000') != '000' or 'shortcode' in args or
              'keyword' in args):
            # Mollie refuses to send UDH headers on for "premium",
            # that is, paid, SMS. Probably due to bureaucratic and
            # legal/ethical reasons. So, we cannot do any SMS
            # concatenation by hand. Instead we do multiple
            # regular messages.
            message_parts = [
                (body, ('%s%c' % (args['reference'], ord('a') + i),
                        None)[args['reference'] is None])
                for i, body in enumerate(sms_split(message, multi_sms_len=160))
            ]
            body_count = len(message_parts)
            # delivery_date = datetime.datetime.now()
            # (above: a failed attempt to get proper ordering)
        else:
            # For free (for the recipient) messages, Mollie will take
            # care of the concatenation. Set body_count to the actual
            # value
            args['type'] = 'long'
            message_parts = [(message, args['reference'])]
            body_count = sms_bodies_needed(len(message), single_sms_len=160,
                                           multi_sms_len=153)

        # GET /xml/sms?username=user&replace_illegal_chars=true \
        # &recipients=%2B31612345678&keyword=NU&md5_password \
        # =123456abcdef123456abcdef123456ab&type=normal&charset=UTF-8 \
        # &mid=ghi&member=false&shortcode=5665&originator=5665 \
        # &message=testing..1..2..3&dlrurl \
        # =http%3A%2F%2Fexample.com%2Fapi%2Fsms%2Fdlr%2F&tariff=025 \
        # &gateway=2&reference=12
        status = 'pnd'  # (assume success first)
        for i, (message, reference) in enumerate(message_parts):
            args['message'] = message.encode('utf-8')
            args['reference'] = reference
            # args['deliverydate'] = (delivery_date +
            #                         datetime.timedelta(seconds=(body_num*3))
            #                        ).strftime('%Y%m%d%H%M%S')

            for attempts in range(3):
                part_status = self._send_part(args)
                if part_status != 'retry':  # do not retry 'nak' and 'pnd'
                    break
                time.sleep(1 << attempts)
            if part_status == 'retry':
                if i == 0:  # not in the middle of something.. break early
                    status = 'retry'
                    break
                part_status = 'nak'

            # set global status
            if part_status == 'nak':
                status = 'nak'

        return status, body_count

    def _send_part(self, args):
        url = self.url + '?' + urllib.parse.urlencode(args)

        log('data: %r' % args, log='sms', subsys='mollie-out',
            fail_silently=True)
        log('url: %r' % url, log='sms', subsys='mollie-out',
            fail_silently=True)

        try:
            # Do not forget the timeout here. Also we need to be wary of
            # a python (2.6/2.7) bug in ssl.py. See these and confirm
            # that it has been fixed locally.
            # http://bugs.python.org/issue5103
            # http://svn.python.org/view?view=rev&revision=80453
            # http://svn.python.org/view/python/branches/release26-maint/\
            #   Lib/ssl.py?r1=80453&r2=80452&pathrev=80453&diff_format=u
            response = urllib.request.urlopen(url, timeout=20)
            responsexml = response.read()
        except urllib.error.URLError as e:  # (should catch more errors here?)
            log('result: %r' % (e.args,), log='sms', subsys='mollie-out',
                fail_silently=True)
            mail_admins(
                'SMS API fail: sms_mollie reference %s' % args['reference'],
                ('Sending message failed with sms_mollie sms backend.\n\n'
                 'URL: %s\n\nData: %r\n\nErrors: %r\n') %
                (url.replace(args['md5_password'], '<hidden>'), args, e.args),
                fail_silently=True
            )
            # This backend is not exactly silent anyway, but silent
            # failing means that we don't need to catch exceptions.
            if not self.fail_silently:
                raise e
            return 'retry'

        log('result: %r' % responsexml, log='sms', subsys='mollie-out',
            fail_silently=True)

        # <?xml version="1.0"?>
        # <response>
        #  <item type="sms">
        #   <recipients>0</recipients>
        #   <success>false</success>
        #   <resultcode>31</resultcode>
        #   <resultmessage>Not enough credits to send message.</resultmessage>
        #  </item>
        # </response>
        dom = parseString(responsexml)
        success = dom.getElementsByTagName('success')[0].childNodes[0].data

        if success != 'true':
            # recipients = int(dom.getElementsByTagName('recipients')[0]
            #                  .childNodes[0].data)
            resultcode = int(dom.getElementsByTagName('resultcode')[0]
                             .childNodes[0].data)
            resultmessage = (dom.getElementsByTagName('resultmessage')[0]
                             .childNodes[0].data)
            mail_admins(
                'SMS API fail: sms_mollie reference %s' % args['reference'],
                ('Sending message failed with sms_mollie sms backend.\n\n'
                 'URL: %s\n\nData: %r\n\nError: %s (%s)\n\nResponse: %s\n') %
                (url.replace(args['md5_password'], '<hidden>'), args,
                 resultmessage, resultcode, responsexml),
                fail_silently=True
            )
            # This backend is not exactly silent anyway, but silent
            # failing means that we don't need to catch exceptions.
            if not self.fail_silently:
                raise ValueError('Gateway error', resultcode, resultmessage)

            if resultcode in (98, 99):
                # 98 "Gateway down"
                # 99 "Unknown error" (should be fixed mid-feb2011)
                return 'retry'

            # Here we can trap 47 "No premium SMS supported for this customer"
            # (which happens to not be in the documentation yet..).
            return 'nak'

        return 'pnd'  # success.. status is pending


def _get_next_mollie_id(text_message, sms_body_count=1):
    '''
    Fetch a mollie_id from the textmessage in a round-robin fashion.
    sms_body_count should be set to how many SMS's are needed for the
    entire body.

    NOTE: This function is more thread-unsafe than others. Django
    already allows multiple objects to be around that are pointing to
    the same data rows. That could in theory already create threading
    problems. This function reads and modifies the TextMessage metadata
    property in a non-atomic fashion, so that's even worse.
    '''
    def lookup_and_modify(meta, sms_body_count):
        # 'meta' is a list of dictionaries by convention: find all
        # 'mollie_id' keys choose the less-used one (as per the
        # mollie_id_used-count).
        low_count, low_item = None, None
        if isinstance(meta, list):
            for meta_item in meta:
                if isinstance(meta_item, dict) and 'mollie_id' in meta_item:
                    # not used yet.. quick exit
                    if 'mollie_id_used' not in meta_item:
                        meta_item['mollie_id_used'] = sms_body_count
                        return meta_item['mollie_id'], meta
                    # store if less often used than other
                    if (low_item is None or
                            meta_item['mollie_id_used'] < low_count):
                        low_count = meta_item['mollie_id_used']
                        low_item = meta_item
        # found one
        if low_item is not None:
            low_item['mollie_id_used'] += sms_body_count
            return low_item['mollie_id'], meta
        return None, None

    # use a helper function so we can save the new meta here
    mollie_id, new_meta = lookup_and_modify(text_message.meta, sms_body_count)
    if mollie_id is not None:
        text_message.meta = new_meta
        text_message.save()
    return mollie_id
