# vim: set ts=8 sw=4 sts=4 et ai:
import datetime
import time

from django import forms
from django.utils.translation import ugettext_lazy as _
from osso.sms import TransientError
from osso.sms.models import Operator, TextMessage
from osso.sms.signals import incoming_message

try:
    from osso.autolog.utils import log
except ImportError:
    log = lambda *x, **y: None


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
    shortcode = forms.CharField(max_length=32, initial='1008', help_text=_('The shortcode that the text message was sent to.'))
    keyword = forms.CharField(max_length=64, initial='EXAMPLE', required=False, help_text=_('The keyword used.'))
    message = forms.CharField(max_length=2048, required=False, initial='example hello world', help_text=_('The full message (including the keyword).'))
    originator = forms.CharField(max_length=32, initial='31612345678', help_text=_('The remote phone number.'))
    operator = forms.CharField(max_length=32, required=False, initial='204-08', help_text=_('Mobile operator code (e.g. "204-08" for KPN Telecom).'))
    mid = forms.CharField(max_length=64, initial='0123456789abcdef', help_text=_('The Mollie message ID. You need this when replying to incoming messages.'))
    subscription = forms.ChoiceField(choices=SUBSCRIPTION_CHOICES, required=False, help_text=_('(Optional) The OK, ON or OFF for a subcription message.'))
    receive_datetime = forms.CharField(max_length=14, initial=now, help_text=_('Time the message was received by the operator.'))

    def __init__(self, *args, **kwargs):
        if 'data' in kwargs:
            log('data: %r' % kwargs['data'], log='sms', subsys='mollie-in', fail_silently=True)
        elif len(args) > 0:
            log('data: %r' % args[0], log='sms', subsys='mollie-in', fail_silently=True)

        # Attempt to merge incoming messages by default.
        # NOTE: When autojoin is enabled, the joined messages are
        # separated by an u2060 WORD JOINER unicode character. That way
        # you can show the breaks if you want and the joining algorithm
        # uses it to calculate whether a new message should be joined at
        # all (i.e. not if the previous message was too short).
        self.autojoin_messages = kwargs.pop('autojoin_messages', True)
        super(IncomingTextMessageForm, self).__init__(*args, **kwargs)

    def clean_message(self):
        message = self.cleaned_data['message']
        # Mollie has fixed the odd escaping. Some providers however
        # replace the ESC with a SPACE for certain extended characters.
        # So, from some operators we get " /" when sending "\\"
        # (because it's sent as "\x1B/"). The EURO sign -- also an
        # extended character -- is decoded properly however.

        # As of 2011-02-05 we regularly get UTF16BE encoded messages.
        # At least from 204-04 numbers. Attempt to decode that.
        if len(message) and len(message) % 4 == 0 and all(i in '0123456789ABCDEF' for i in message):
            utf16 = []
            for i in range(0, len(message), 2):
                utf16.append(chr(int(message[i:(i + 2)], 16)))
            try:
                decoded = ''.join(utf16).decode('UTF-16BE')
            except UnicodeDecodeError:
                pass
            else:
                # Double-check that the resulting string is not garbage
                # by looking for a percentage of expected ascii.
                ascii = [i in 'ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789 ' for i in decoded]
                ascii_pct = float(len([i for i in ascii if i])) / len(ascii)
                if ascii_pct >= 0.25:
                    log('data: decoded %r to %r' % (message, decoded), log='sms', subsys='mollie-in', fail_silently=True)
                    message = decoded  # use the decoded message

        # Replace any \u2060 with \ufeff because we use 2060 internally.
        return message.replace('\u2060', '\ufeff')  # we use 2060 as concat delim

    def clean_operator(self):
        # Get the operator, but do not die if this fails.
        try:
            oper, created = Operator.objects.get_or_create(entire_code=self.cleaned_data['operator'])
        except AssertionError:
            return None
        return oper

    def clean_originator(self):
        value = self.cleaned_data['originator'].strip()
        if any(i not in '0123456789' for i in value) or len(value) == 0 or value[0] == '0':
            raise forms.ValidationError(_('Expected phone number to be clean and complete.'))
        return '+%s' % value

    def clean_receive_datetime(self):
        try:
            value = time.strptime(self.cleaned_data['receive_datetime'], '%Y%m%d%H%M%S')
            value = datetime.datetime(*value[:6])
        except ValueError:
            raise forms.ValidationError(_('The time does not have the required formatting, expected YYYYmmddHHMMSS.'))
        return value

    def save(self):
        body = self.cleaned_data['message']

        # Combine keyword with shortcode/destination to form the local
        # address.
        keyword = self.cleaned_data['keyword'].upper()
        local_address = ('%s %s' % (self.cleaned_data['shortcode'], keyword)).strip()

        # Data for which the TextMessage object has no properties goes
        # in the meta property.
        meta = {'mollie_id': self.cleaned_data['mid']}
        if self.cleaned_data['subscription'] != '':
            meta['subscription'] = self.cleaned_data['subscription']

        # Find a message to pair with. This is ugly right here, because
        # there is nothing but the timestamp that says that two messages
        # should be merged.
        message = None
        if self.autojoin_messages:
            merge_candidates = TextMessage.objects.filter(
                status='in',
                local_address__startswith=self.cleaned_data['shortcode'],  # keywords may be appended by app
                remote_address=self.cleaned_data['originator'],
                remote_operator=self.cleaned_data['operator'],
                delivery_date__lte=self.cleaned_data['receive_datetime'],
                delivery_date__gte=self.cleaned_data['receive_datetime'] - datetime.timedelta(seconds=7)
            ).order_by('-delivery_date')

            if len(merge_candidates) != 0:
                message = merge_candidates[0]
                # Second check, to be on the safe side. The last message
                # must be 153 or 67 septets long. (For GSM-charset, it
                # can be more, with the odd s/\x1B/ /g replacements
                # going on.)
                last_part = message.body.split('\u2060')[-1]
                # A bit of odd logic here: at this point, we don't know
                # if the message was in ucs-2 or gsm-0338, so we need to
                # check both lengths.
                if len(last_part) == 67:
                    pass  # ucs2-encoded multipart
                else:
                    try:
                        if len(last_part.encode('gsm-0338')) < 153:
                            message = None
                    except UnicodeEncodeError:
                        if len(last_part) < 67:
                            message = None

        # Append message or create a new one.
        if message is not None:
            # Long messages can arrive several seconds apart. Store the newer
            # delivery_date.
            meta['prev_delivery_date'] = message.delivery_date
            message.delivery_date = self.cleaned_data['receive_datetime']
            # Append the message delimited by a word-joiner (zero width,
            # no breaks).
            message.body += '\u2060' + body
            message.body_count += 1
            message.meta_append(meta, commit=False)
            assert len([i for i in message.body if i == '\u2060']) + 1 == message.body_count
            message.save()
            incoming_message.send(sender=TextMessage, instance=message, appended=True)
        else:
            message = TextMessage.objects.create(
                status='in',
                local_address=local_address,
                remote_address=self.cleaned_data['originator'],
                remote_operator=self.cleaned_data['operator'],
                body=body,
                delivery_date=self.cleaned_data['receive_datetime'],
                meta=[meta]
            )
            incoming_message.send(sender=TextMessage, instance=message, appended=False)

        return message


class DeliveryReportForm(forms.Form):
    '''
    The SMS gateway calls this for delivery report of outbound text
    messages.
    http://www.mollie.nl/support/documentatie/sms-diensten/keyword/mo/
    '''
    reference = forms.CharField(max_length=64, initial='1', help_text=_('Text message reference (max 60 chars).'))
    recipient = forms.CharField(max_length=32, initial='31612345678', help_text=_('The remote phone number.'))
    status = forms.ChoiceField(choices=STATUS_CHOICES, initial=50, help_text=_('The status code.'))

    def __init__(self, *args, **kwargs):
        if 'data' in kwargs:
            log('data: %r' % kwargs['data'], log='sms', subsys='mollie-dlr', fail_silently=True)
        elif len(args) > 0:
            log('data: %r' % args[0], log='sms', subsys='mollie-dlr', fail_silently=True)
        super(DeliveryReportForm, self).__init__(*args, **kwargs)

    def clean_reference(self):
        # When we send long messages we append a letter to the
        # textmessage id to separate the distinct parts.
        value = self.cleaned_data['reference'].strip()
        if value[-1] in 'abcdefghijklmnopqrstuvwxyz':
            letter = value[-1]
            value = value[0:-1]
        else:
            letter = None

        try:
            value = TextMessage.objects.get(id=int(value))
            value.id_suffix = letter  # hack ;)
        except (ValueError, TextMessage.DoesNotExist):
            raise forms.ValidationError(_('Reference not found.'))
        return value

    def clean_recipient(self):
        value = self.cleaned_data['recipient'].strip()
        if any(i not in '0123456789' for i in value) or len(value) == 0 or value[0] == '0':
            raise forms.ValidationError(_('Expected phone number to be clean and complete.'))
        return '+%s' % value

    def clean_status(self):
        try:
            value = int(self.cleaned_data['status'])
            assert 50 <= value <= 59
        except (AssertionError, ValueError):
            raise forms.ValidationError(_('Expected status value between 50 and 59.'))
        return value

    def clean(self):
        # Double check: compare the message state and recipient
        message = self.cleaned_data.get('reference')
        if message:
            if message.remote_address != self.cleaned_data['recipient']:
                raise forms.ValidationError(_('Reference, recipient and status mismatch (a).'))
            if message.status == 'in':
                raise forms.ValidationError(_('Reference, recipient and status mismatch (b).'))
            # Mollie sometimes sends the DLR twice where it only listens to
            # the 500 error of the second message.
            #if message.id_suffix is None and message.status in ('ack', 'nak'):
            #    raise forms.ValidationError(_(u'Reference, recipient and status mismatch (c).'))
        return self.cleaned_data

    def save(self):
        # Get the message by reference; we've already checked it in
        # clean().
        message = self.cleaned_data['reference']

        # Set message status.
        # XXX: moeten 55 en 56 bij failed of bij pending?
        statuscode = self.cleaned_data['status']
        if statuscode == 50:
            if message.status in ('out', 'pnd'):
                message.status = 'ack'  # success
                message.delivery_date = datetime.datetime.now()
        elif statuscode in (51, 52, 55, 56):
            if message.status == 'out':
                message.status = 'pnd'  # pending
        else:
            message.status = 'nak'  # failed
            if message.delivery_date is None:
                message.delivery_date = datetime.datetime.now()

        # Add status code to the metadata.
        metadata = {'mollie_status': statuscode}
        if message.id_suffix is not None:
            metadata['part'] = message.id_suffix

        try:
            message.meta_append(metadata, commit=False)
        except AssertionError:
            # If we get a DLR report when the metadata is not "clean"
            # the sms is still being sent. (Quite possible if Mollie is
            # fast and we're sending multipart sms.)
            raise TransientError()

        message.save()
        return message
