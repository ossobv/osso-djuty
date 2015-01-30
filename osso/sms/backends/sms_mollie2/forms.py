# vim: set ts=8 sw=4 sts=4 et ai:
import base64
import datetime
import time

from django import forms
from django.core.mail import mail_admins
from django.utils.translation import ugettext_lazy as _
from osso.sms.models import Operator, TextMessage, TextMessageExtra
from osso.sms.backends.sms_mollie2 import decode_message

try:
    from osso.autolog.utils import log
except ImportError:
    log = lambda *x, **y: None


# 2011-03-17: Rick Wong @ Mollie schrijft:
# > Wij hebben een verandering klaar staan die ongeveer werkt zoals de
# > oplossing die u adviseerde. Voor uw shortcode 1234 geldt, zodra de
# > verandering live gezet wordt, dat de volgende variabelen
# > meegestuurd worden:
# > * messagetype
# > * header [UDH in HEX zonder length byte]
# > * dcs [Data Coding Scheme octet]
# > messagetype kan twee mogelijke numerieke waarden hebben:
# > * 10: de body is tekstueel [lees: vergeet de DCS]
# > * 11: de body is binair [lees: in HEX, DCS moet gebruikt worden]
MESSAGETYPE_CHOICES = (
    ('', _('(undefined)')),  # the three extra headers not sent by default
    ('10', _('Textual (decoded) message.')),
    ('11', _('Binary (HEX-encoded) message.')),
)


STATUS_CHOICES = (
    (0, _('---')),
    (50, _('Delivered')),
    (51, _('Sent')),
    (52, _('Buffered')),
    (53, _('Delivery failed')),
    (54, _('Delivery disallowed/impossible')),
    (55, _('Destination disabled')),
    (56, _('Destination unresponsive')),
    (57, _('Destination failure')),
    (58, _('Destination memory full')),
    (59, _('Unknown destination')),
)

# Het blijkt toch moeilijk bij Mollie om je eigen documentatie te
# volgen/updaten.
#
# 2010-03-21: Adriaan Mol @ Mollie schrijft nadat ik geklaagd heb dat
# er niet "on" en "off" gestuurd wordt:
# > Het is inderdaad beide in "uppercases", apart dat dit niet meer goed
# > staat in de documentatie. We zullen aankomende week de documentatie-
# > pagina updaten bij de eerstvolgende nieuwe release van Mollie.
# > Excuses voor de verwarring in ieder geval en bedankt voor je
# > alertheid.
#
# 2010-04-04: Adriaan Mol @ Mollie schrijft belerend het volgende, nadat
# ik geklaagd heb over de onbekende/nieuwe waarde "OK":
# > "OK" en "JA"  is inderdaad een nieuw. Redelijk recentelijk
# > toegevoegd vanwege de striktere Opta-regels. Beide worden omgezet
# > naar "OK".
# >
# > Het is goed om strikt te programmeren, maar de waarde van een
# > parameter die alleen als hulpmiddel bestaat en die je niet gebruikt
# > lijkt mij onnodig om te controleren of jouw beredenering van de
# > waarde overeenkomt met die van ons. Zeker omdat het om geld gaat
# > moet deze loze check geen showstopper zijn. Het lijkt me daarom geen
# > fatale error.
SUBSCRIPTION_CHOICES = (
    ('', _('---')),
    ('OFF', _('Off')),  # off/uit/stop
    ('OK', _('Confirmed')),  # ja/ok
    ('ON', _('On')),  # aan/on
)


def now():
    return datetime.datetime.now().strftime('%Y%m%d%H%M%S')


class IncomingTextMessageForm(forms.Form):
    '''
    The SMS gateway calls this for incoming text messages.
    http://www.mollie.nl/support/documentatie/sms-diensten/keyword/mo/
    '''
    shortcode = forms.CharField(max_length=32, initial='1008',
        help_text=_('The shortcode that the text message was sent to.'))
    keyword = forms.CharField(max_length=64, initial='EXAMPLE', required=False,
        help_text=_('The keyword used.'))
    message = forms.CharField(max_length=2048, required=False,
        initial='example hello world',
        help_text=_('The full message (including the keyword).'))
    originator = forms.CharField(max_length=32, initial='31612345678',
        help_text=_('The remote phone number.'))
    operator = forms.CharField(max_length=32, required=False, initial='204-08',
        help_text=_('Mobile operator code (e.g. "204-08" for KPN Telecom).'))
    mid = forms.CharField(max_length=64, initial='0123456789abcdef',
        help_text=_('The Mollie message ID. You need this when replying to '
                    'incoming messages.'))
    subscription = forms.ChoiceField(choices=SUBSCRIPTION_CHOICES,
        required=False,
        help_text=_('(Optional) The OK, ON or OFF for a subcription message.'))
    receive_datetime = forms.CharField(max_length=14, initial=now,
        help_text=_('Time the message was received by the operator.'))

    # New fields, introduced after communication with Mollie:
    # 10 = text message, 11 = hex message
    messagetype = forms.ChoiceField(choices=MESSAGETYPE_CHOICES,
        required=False, help_text=_('(Optional) Message body type.'))
    dcs = forms.IntegerField(min_value=0, max_value=255, required=False,
        help_text=_('(Optional) Data coding scheme (&0x80=compress, '
                    '&0xC=charset), only use if messagetype is binary. '
                    'E.g. 0 for regular septet/GSM-03.38 encoding and 8 '
                    'for UCS2.'))
    header = forms.CharField(max_length=(139 * 2), required=False, initial='',
        help_text=_('(Optional) UDH without header-length byte in '
                    'hexadecimal.'))  # e.g. '00031D0201'

    def __init__(self, *args, **kwargs):
        if 'data' in kwargs:
            log('data: %r' % kwargs['data'], log='sms', subsys='mollie2-in',
                fail_silently=True)
        elif len(args) > 0:
            log('data: %r' % args[0], log='sms', subsys='mollie2-in',
                fail_silently=True)

        super(IncomingTextMessageForm, self).__init__(*args, **kwargs)

    def clean_message(self):
        message = self.cleaned_data['message']
        # Mollie has fixed the odd escaping. Some providers however
        # replace the ESC with a SPACE for certain extended characters.
        # So, from some operators we get " /" when sending "\\"
        # (because it's sent as "\x1B/"). The EURO sign -- also an
        # extended character -- is decoded properly however.
        return message

    def clean_operator(self):
        # Get the operator, but do not die if this fails.
        try:
            oper, created = Operator.objects.get_or_create(
                entire_code=self.cleaned_data['operator'])
        except AssertionError:
            return None
        return oper

    def clean_originator(self):
        value = self.cleaned_data['originator'].strip()
        if (any(i not in '0123456789' for i in value) or len(value) == 0 or
                value[0] == '0'):
            raise forms.ValidationError(_('Expected phone number to be '
                                          'clean and complete.'))
        return '+%s' % value

    def clean_receive_datetime(self):
        try:
            value = time.strptime(self.cleaned_data['receive_datetime'],
                                  '%Y%m%d%H%M%S')
            value = datetime.datetime(*value[:6])
        except ValueError:
            raise forms.ValidationError(_('The time does not have the '
                                          'required formatting, expected '
                                          'YYYYmmddHHMMSS.'))
        return value

    def clean_header(self):
        header = self.cleaned_data['header']
        if len(header) % 2 != 0 or any(i not in '0123456789ABCDEF'
                                       for i in header):
            raise forms.ValidationError(_('Header is expected to be '
                                          'HEX-encoded.'))
        data = []
        for i in range(0, len(header), 2):
            data.append(int(header[i:(i + 2)], 16))
        return data

    def clean(self):
        # Check the messagetype/dcs and decode message if needed.
        message = self.cleaned_data.get('message')
        messagetype = self.cleaned_data.get('messagetype', '')

        if message is not None:
            if messagetype == '':  # legacy
                if (self.cleaned_data.get('dcs') is not None or
                        self.cleaned_data.get('header')):
                    raise forms.ValidationError(
                        _('Unexpected dcs and/or header fields for (legacy) '
                          'unset messagetype.'))
                # Attempt to decode message by guessing:
                message = decode_message(message)
                # Explicitly set it to unset
                self.cleaned_data['header'] = None
            else:
                dcs = self.cleaned_data.get('dcs')
                header = self.cleaned_data.get('header', '')
                if messagetype == '10':
                    pass  # text: ignore dcs.. Mollie did the decoding
                elif messagetype == '11':
                    if dcs is None:
                        # Mollie suxors the boxors at times. Now they
                        # don't obey their own protocol again.  Parse it
                        # anyway instead of throwing an error.
                        # raise forms.ValidationError(
                        #     _('Expected dcs field for binary message.'))
                        # This is always "Operator: 204-16 T-Mobile (nl)".
                        try:
                            chars = [unichr(int(message[i:(i + 4)], 16))
                                     for i in range(0, len(message), 4)]
                            message_txt = u''.join(chars)
                        except Exception as e:
                            message_txt = u'<UNDECIPHERABLE: %r / %s>' % (e, e)
                        mail_admins(
                            'Mollie is missing DCS in binary message :(',
                            ('Message was: %r\nUDH: %r\nGuess: %r\n'
                             'Remote-Addr: %r\nRemote-Oper: %r') %
                            (message, header, message_txt,
                             self.cleaned_data.get('originator'),
                             self.cleaned_data.get('operator')),
                            fail_silently=True
                        )
                    # Binary
                    message = decode_message(message, dcs=dcs, udh=header)
                    if isinstance(message, str):  # vs. unicode
                        # Let the save method know this is not a string
                        message = [ord(i) for i in message]
                else:
                    assert False, 'Programming error'
                # Explicitly set it to empty if unset
                self.cleaned_data['header'] = header

            self.cleaned_data['message'] = message

        return self.cleaned_data

    def save(self):
        meta = {}
        if self.cleaned_data['subscription'] != '':
            # Not very useful
            meta['subscription'] = self.cleaned_data['subscription']

        if self.cleaned_data['header'] is not None:
            meta['udh'] = self.cleaned_data['header']
        if isinstance(self.cleaned_data['message'], list):
            # In case of a list of bytes, set meta bin to True and
            # base64 encode the data so it comes out unmodified.
            chars = [chr(i) for i in self.cleaned_data['message']]
            self.cleaned_data['message'] = base64.b64encode(''.join(chars))
            meta['bin'] = True
        if meta:
            meta = [meta]
        else:
            meta = None

        message = TextMessage.objects.create(
            status='in',
            local_address=self.cleaned_data['shortcode'],
            remote_address=self.cleaned_data['originator'],
            remote_operator=self.cleaned_data['operator'],
            body=self.cleaned_data['message'],
            delivery_date=self.cleaned_data['receive_datetime'],
            meta=meta
        )
        # Store mollie-specific stuff here instead of in the meta var.
        TextMessageExtra.objects.create(
            textmessage=message,
            shortcode=self.cleaned_data['shortcode'],
            keyword=self.cleaned_data['keyword'],
            foreign_reference=self.cleaned_data['mid'],
        )
        return message


class DeliveryReportForm(forms.Form):
    '''
    The SMS gateway calls this for delivery report of outbound text
    messages.
    http://www.mollie.nl/support/documentatie/sms-diensten/keyword/mo/
    '''
    reference = forms.CharField(max_length=61, initial='1',
        help_text=_('Text message reference (max 60 chars).'))
    recipient = forms.CharField(max_length=31, initial='31612345678',
        help_text=_('The remote phone number.'))
    status = forms.ChoiceField(choices=STATUS_CHOICES, initial=50,
        help_text=_('The status code.'))

    def __init__(self, *args, **kwargs):
        if 'data' in kwargs:
            log('data: %r' % kwargs['data'], log='sms', subsys='mollie2-dlr',
                fail_silently=True)
        elif len(args) > 0:
            log('data: %r' % args[0], log='sms', subsys='mollie2-dlr',
                fail_silently=True)
        super(DeliveryReportForm, self).__init__(*args, **kwargs)

    def clean_reference(self):
        try:
            value = TextMessage.objects.get(
                id=int(self.cleaned_data['reference'].strip()))
        except (ValueError, TextMessage.DoesNotExist):
            raise forms.ValidationError(_('Reference not found.'))
        return value

    def clean_recipient(self):
        value = self.cleaned_data['recipient'].strip()
        if (any(i not in '0123456789' for i in value) or len(value) == 0 or
                value[0] == '0'):
            raise forms.ValidationError(_('Expected phone number to be clean '
                                          'and complete.'))
        return '+%s' % value

    def clean_status(self):
        try:
            value = int(self.cleaned_data['status'])
            assert 50 <= value <= 59
        except (AssertionError, ValueError):
            raise forms.ValidationError(_('Expected status value between '
                                          '50 and 59.'))
        return value

    def clean(self):
        # Double check: compare the message state and recipient
        message = self.cleaned_data.get('reference')
        if message:
            if message.remote_address != self.cleaned_data['recipient']:
                raise forms.ValidationError(_('Reference, recipient and '
                                              'status mismatch (a).'))
            if message.status in ('in', 'rd'):
                raise forms.ValidationError(_('Reference, recipient and '
                                              'status mismatch (b).'))
        return self.cleaned_data

    def save(self):
        message = self.cleaned_data['reference']
        statuscode = self.cleaned_data['status']
        now = datetime.datetime.now()

        # The filters below allow status to be out even though they're
        # already set to pnd by the send-algorithm. In case of a race,
        # allowing out as well, is beneficial.
        if statuscode == 50:
            # ack = success
            filter = {'status__in': ('out', 'pnd')}
            update = {'status': 'ack', 'delivery_date': now, 'modified': now}
        elif statuscode in (51, 52):
            # pnd = pending
            # (because this doesn't include pnd, we do not update)
            filter = {'status': 'out'}
            update = {'status': 'pnd', 'modified': now}
        else:
            # nak = failed
            filter = {'status__in': ('out', 'pnd')}
            update = {'status': 'nak', 'delivery_date': now, 'modified': now}

        rowcount = TextMessage.objects.filter(
            id=message.id, delivery_date=None, **filter).update(**update)
        assert rowcount in (0, 1)
        if (rowcount == 0 and  # pnd => pnd is okay
                not (message.status == 'pnd' == update.get('status'))):
            # This should not happen. Possible cases when this might,
            # are when an ack is sent twice (delivery_date is set on the
            # second try) or if DLRs are sent out of order.
            mail_admins(
                u'SMS API warn: sms_mollie2 reference %s' % (message.id,),
                (u'DLR caused an update of 0 rows.\nIn data: %r\n'
                 u'Orig data: %r\n') %
                (self.cleaned_data, (message.status, message.delivery_date)),
                fail_silently=True
            )

        return message
