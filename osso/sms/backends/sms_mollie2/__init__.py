# vim: set ts=8 sw=4 sts=4 et ai:
# See documentation at:
# * http://www.mollie.nl/support/documentatie/sms-diensten/keyword/mo/
# * http://www.mollie.nl/support/documentatie/sms-diensten/sms/http/?s=premium
# * http://www.mollie.nl/support/documentatie/sms-diensten/dlr/
# (parts taken from m3r consultancy mollie-python-1.0.0 example by Ivo
# van der Wijk)
import urllib.request, urllib.parse, urllib.error
import urllib.request, urllib.error, urllib.parse
from xml.dom.minidom import parseString

from django.core.mail import mail_admins
from osso.aboutconfig.utils import aboutconfig
from osso.sms import BaseSmsBackend, DestinationError
from osso.sms.models import TextMessageExtra

try:
    from osso.autolog.utils import log
except ImportError:
    log = lambda *x, **y: None


GATEWAY_CHOICES = (
    (2, 'Basic'),
    (50, 'Belgium ($$$)'),  # duur
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
        self.url = (aboutconfig('sms.backends.sms_mollie.url', URL_CHOICES[0])
                    .encode('utf-8'))
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
            # above: or 'http://...' + reverse('sms_delivery_report')

    def send_messages(self, sms_messages, reply_to=None,
                      shortcode_keyword=None, tariff_cent=None):
        # We should probably remove the assertion and make it compatible
        # with molliev1.
        assert (reply_to is None and shortcode_keyword is None and
                tariff_cent is None), 'We use TextMessageExtra only.'
        sent = 0
        for message in sms_messages:
            if self.send_sms(message):
                sent += 1
        return sent

    def send_sms(self, message):
        '''
        Use the mollie gateway to send out a message. The only
        difference between "premium" and "regular" sms is really
        whether we can charge the user or not. So the tariff_cent
        decides which type we'll use. Like the other extra parameters
        this should be found in the TextMessageExtra addon. If there
        is no such item, the tariff_cent will be assumed to be 0.

        For all premium sms, we must add a couple of parameters:
        tariff, (member), shortcode, keyword, (mid). These are required
        to be found in the TextMessageExtra add-on.

        For non-subscription premium sms you need the Mollie mid
        parameter for replies. For subscription premium sms, you do not
        need the mid, but must use the correct shortcode and keyword.
        '''
        try:
            extra = message.extra
        except TextMessageExtra.DoesNotExist:
            is_premium = False
        else:
            is_premium = bool(extra.tariff_cent)

        # Select optional parameters from the metadata. For now we only
        # accept 'gateway'.
        gateway = None  # none means default, other means override
        meta = message.meta
        if meta and isinstance(meta, list) and isinstance(meta[0], dict):
            gateway = meta[0].get('gateway')
        elif not is_premium and message.remote_operator:
            # Optionally use custom gateway for specific countries, like
            # 1 (business+) for Vodafone which is unreliable with 2
            # (regular). Same for Belgium where 50 is more reliable and
            # it doesn't unnecessarily quote-enclose the shortcode.
            # sms.backends.sms_mollie.gateway.204.04 = 1
            # sms.backends.sms_mollie.gateway.206 = 50
            oper_cc, oper_oc = (message.remote_operator.entire_code()
                                .split('-'))  # quick
            gateway = (
                aboutconfig('sms.backends.sms_mollie.gateway.%s.%s' %
                            (oper_cc, oper_oc))
                or aboutconfig('sms.backends.sms_mollie.gateway.%s' %
                               (oper_cc,))
                or None  # aboutconfig returns '' by default if not found
            )

        # Compile premium_args
        if is_premium:
            # Attempt to match the tariff to the available choices:
            # select one of the TARIFF_CHOICES, rounding upwards if
            # there is no exact match.
            tariff_cent = int(extra.tariff_cent)
            tariff_cent = ([j for i, j in enumerate(TARIFF_CHOICES)
                            if ((-1,) + TARIFF_CHOICES)[i] < tariff_cent
                                                           <= j]   # noqa
                           or [TARIFF_CHOICES[-1]])[0]
            # It is either a reply or a subscription message.
            mollie_id = extra.foreign_reference or None
            subscribed = not mollie_id

            premium_args = {
                'tariff': '%03d' % tariff_cent,  # a three-char tariff
                'member': ('false', 'true')[bool(subscribed)],
            }
            if extra.shortcode is not None:
                premium_args['shortcode'] = \
                    str(extra.shortcode).encode('utf-8')
            if extra.keyword is not None:
                premium_args['keyword'] = \
                    str(extra.keyword).encode('utf-8')
            if mollie_id:
                premium_args['mid'] = str(mollie_id).encode('utf-8')
        else:
            premium_args = None

        # Send it on
        new_status, body_count = self._send(
            body=message.body,
            recipient_list=[message.remote_address],
            local_address=message.local_address,
            gateway=gateway,
            reference=message.id,
            premium_args=premium_args
        )

        # Update info and return status
        assert body_count == message.body_count or message.body_count == 1, \
            ('Expected lazy mans 1 or correct body count (%d != %d for %d)' %
             (body_count, message.body_count, message.id))
        message.body_count = body_count
        if new_status != 'retry':  # some things you have to try again
            message.status = new_status
        message.save()
        return new_status == 'pnd'  # moved to pending => success

    def _send(self, body, recipient_list, local_address, gateway=None,
              reference=None, premium_args=None):
        '''
        Returns a tuple with the text message status and the number of
        text message bodies needed.
        '''
        args = self.default_args.copy()
        args['recipients'] = ','.join(recipient_list).encode('utf-8')
        args['originator'] = local_address.encode('utf-8')
        if gateway is not None:
            args['gateway'] = str(gateway).encode('utf-8')
        if reference is not None:
            args['reference'] = str(reference).encode('utf-8')

        if premium_args:
            args.update(premium_args)

        # Ensure that we send no illegal characters and take the correct
        # message length into account.
        body_0338 = body.encode('gsm-0338', 'replace')
        length = len(body_0338)
        body_utf8 = body_0338.decode('gsm-0338').encode('utf-8')

        # The message
        args['message'] = body_utf8

        # """Via de API is het mogelijk maximaal 1377 tekens per bericht te
        # gebruiken. Het bericht wordt opgesplitst in delen van 153 tekens, in
        # maximaal 9 SMS-berichten. (9x 153 tekens).
        # Let op! U betaalt per verzonden SMS-bericht. Bij een bericht met 300
        # tekens worden 2 SMS-berichten verstuurd."""
        if length <= 160:
            body_count = 1
        else:
            assert 'tariff_cent' not in args, \
                'We do cannot do long paid SMS.'  # premium
            # Mollie does accept custom UDH, so we could do long paid
            # SMS, except that legislations/ethics prohibits that.
            # Sending the UDH yourself involves filling the 'udh'
            # parameter with hexadecimal values, setting the type to
            # 'binary' and filling the message body with Windows-1252-
            # encoded data. (Note that UDH takes room from the body.)
            # See: http://en.wikipedia.org/wiki/Concatenated_SMS
            args['type'] = 'long'
            body_count = ((length - 1) / 153) + 1

        # GET /xml/sms?username=user&replace_illegal_chars=true \
        # &recipients=%2B31612345678&keyword=NU&md5_password \
        # =123456abcdef123456abcdef123456ab&type=normal&charset=UTF-8 \
        # &mid=ghi&member=false&shortcode=5665&originator=5665 \
        # &message=testing..1..2..3 \
        # &dlrurl=http%3A%2F%2Fexample.com%2Fapi%2Fsms%2Fdlr%2F \
        # &tariff=025&gateway=2&reference=12
        url = self.url + '?' + urllib.parse.urlencode(args)
        log('data: %r' % args, log='sms', subsys='mollie2-out',
            fail_silently=True)
        log('url: %r' % url, log='sms', subsys='mollie2-out',
            fail_silently=True)

        try:
            # Do not forget the timeout here. Also we need to be wary of
            # a python bug in ssl.py. See these and confirm that it has
            # been fixed locally.
            # http://bugs.python.org/issue5103
            # http://svn.python.org/view?view=rev&revision=80453
            # http://svn.python.org/view/python/branches/release26-maint/ \
            #   Lib/ssl.py?r1=80453&r2=80452&pathrev=80453&diff_format=u
            response = urllib.request.urlopen(url, timeout=20)
            responsexml = response.read()
        except urllib.error.URLError as e:  # (SSLError is a URLError too)
            log('result: %r' % (e.args,), log='sms', subsys='mollie2-out',
                fail_silently=True)
            if not self.fail_silently:
                raise ValueError('Gateway communication error', *e.args)
            return 'retry', body_count  # you should retry this

        log('result: %r' % responsexml, log='sms', subsys='mollie2-out',
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

            if not self.fail_silently:
                # Error 47 may happen: the client will never be able to
                # pay for premium SMS.
                if resultcode == 47:
                    raise DestinationError(('Destination will fail for '
                                            'paid SMS'),
                                           resultcode, resultmessage)

                # The other errors should not happen if we're supplying
                # the right parameters.
                raise ValueError('Gateway error', resultcode, resultmessage)

            # Even in fail_silently mode, we're still verbose as there
            # is a chance that this is a programming error.
            mail_admins(
                'SMS API fail: sms_mollie2 reference %s' % args['reference'],
                ((('Sending message failed with sms_mollie2 sms backend.\n\n'
                  'URL: %s\n\nData: %r\n\nError: %s (%s)\n\nResponse: %s\n') %
                 (url, args, resultmessage, resultcode, responsexml))
                 .replace(args['md5_password'], 'CENSORED')),
                fail_silently=True
            )
            if resultcode in (98, 99):
                # 98 "Gateway down"
                # 99 "Unknown error" (should be fixed mid-feb2011)
                return 'retry', body_count

            # Here we can trap 47 "No premium SMS supported for this customer"
            # (which happens to not be in the documentation yet..).
            return 'nak', body_count

        return 'pnd', body_count


def parse_dcs(dcs):
    assert 0 <= dcs <= 255, 'Expected DSC to be in 0..255, value: %r' % (dcs,)
    encodings = ('gsm-0338', None, 'utf-16be', None)  # dfl, 8bit, UCS-2, rsvrd
    # Immediate display, Mobile Equipment specific, SIM.., Terminal
    # Equipment..
    classes = ('ALERT', 'ME', 'SIM', 'TE')
    ret = {}
    # Regular TEXT
    if (dcs & 0xc0) == 0:
        ret['compressed'] = bool(dcs & 0x20)
        ret['encoding'] = encodings[(dcs & 0xc) >> 2]
        if dcs & 0x10:
            ret['class'] = classes[dcs & 0x3]
    # Data message
    elif (dcs & 0xf0) == 0xf0 and (dcs & 0x8) == 0:
        ret['compressed'] = False
        ret['encoding'] = encodings[(dcs & 0x4) >> 2]  # only first two options
        ret['class'] = classes[dcs & 0x3]
    # Message waiting indication (or data with 3rd bit set)
    else:
        pass  # Parse DCS of MWI not implemented yet..

    return ret


def decode_message(message, dcs=None, udh=[]):
    '''
    Can return str or unicode, depending on the data. Mind it!

    message is a binary string,
    dcs is an integer between 0 and 255 (optional),
    udh is a list of integers in 0..255 (optional).

    Note that we need to take the UDH length and last bits into account
    when decoding binary septet-encoded messages -- if we were to
    implement that ;)
    '''
    is_in_hex = (message and len(message) % 2 == 0 and
                 all(i in '0123456789ABCDEF' for i in message))

    if dcs is None:
        # As of 2011-02-05 we regularly get UCS-2-encoded messages.
        # If we don't have the newer DCS headers, use a heuristic to see
        # if this is HEX-encoded UCS-2.
        if not is_in_hex or not len(message) % 4 == 0:
            return message  # not 2-byte hex
        ucs2 = []
        for i in range(0, len(message), 2):
            ucs2.append(chr(int(message[i:(i + 2)], 16)))
        try:
            decoded = ''.join(ucs2).decode('utf-16be')
        except UnicodeDecodeError:
            # Decode error?  Then it wasn't UTF-16 (might've been UCS-2
            # though.. ah, whatever)
            return message
        # Double-check that the resulting string is not garbage
        # by looking for a percentage of expected ascii.
        ascii = [i in ('ABCDEFGHIJKLMNOPQRSTUVWXYZ'
                       'abcdefghijklmnopqrstuvwxyz0123456789 ')
                 for i in decoded]
        ascii_pct = float(len([i for i in ascii if i])) / len(ascii)
        if ascii_pct < 0.25:
            return message
        log('data: decoded %r to %r' % (message, decoded),
            log='sms', subsys='mollie2', fail_silently=True)
        return decoded

    # Okay. As of 2011-03-17, we get more info: udh and dcs.  If the
    # messagetype was "text", you shouldn't have called this.  If it is
    # "binary", you've come to the right place.
    assert is_in_hex, ('Expected message to be HEX-encoded, value: %r' %
                       (message,))
    dcsdata = parse_dcs(dcs)
    log('data: parsed data coding scheme %r' % (dcsdata,),
        log='sms', subsys='mollie2', fail_silently=True)
    assert not dcsdata.get('compressed', False), \
        'Unable to handle compressed messages, dcs: %r' % (dcs,)
    assert 'encoding' in dcsdata, \
        'Unable to continue without known encoding, dcs: %r' % (dcs,)

    # (1) Decode to binary string
    data = []
    for i in range(0, len(message), 2):
        data.append(chr(int(message[i:(i + 2)], 16)))
    data = ''.join(data)

    # (2) Decode if necessary (mind the return value!)
    if dcsdata['encoding']:
        assert dcsdata['encoding'] != 'gsm-0338', \
            'Do we need to unpack7? What about UDH alignment?'
        data = data.decode(dcsdata['encoding'])

    return data  # can be str or unicode
