# vim: set ts=8 sw=4 sts=4 et ai:
import datetime, time
from django import forms
from django.utils.translation import ugettext_lazy as _
from osso.core.forms.fields import PhoneNumberField
from osso.sms.models import Operator, TextMessage, TextMessageExtra
from osso.sms.signals import incoming_message

try: from osso.autolog.utils import log
except ImportError: log = lambda *x, **y: None


class IncomingTextMessageForm(forms.Form):
    '''
    Our own SMS gateway calls this for incoming subscriptions and
    unsubscribe messages.
    '''
    delivery_date = forms.CharField(max_length=10, initial=lambda: int(time.time()), help_text=_(u'Time the message was received by the operator (unixtime).'))
    remote_address = PhoneNumberField(initial='+31612345678', help_text=_(u'The remote phone number.'))
    remote_operator = forms.CharField(max_length=32, required=False, initial='204-08', help_text=_(u'Mobile operator code (e.g. "204-08" for KPN Telecom).'))
    local_address = forms.CharField(max_length=32, initial='1008 GOD', help_text=_(u'The shortcode plus keyword that the message was sent to.'))
    body = forms.CharField(max_length=4096, required=False, initial='ON', help_text=_(u'The parsed message body, without keywords. ON or OFF for subscription messages.'))
    body_count = forms.IntegerField(required=False, initial=1, min_value=1, help_text=_(u'How many bodies the message consists of.'))
    id = forms.IntegerField(required=False, help_text=_(u'An identifier to use when replying.'))

    def __init__(self, *args, **kwargs):
        if 'data' in kwargs:
            log('data: %r' % kwargs['data'], log='sms', subsys='zjipz-in', fail_silently=True)
        elif len(args) > 0:
            log('data: %r' % args[0], log='sms', subsys='zjipz-in', fail_silently=True)

        super(IncomingTextMessageForm, self).__init__(*args, **kwargs)

    def clean_delivery_date(self):
        try:
            value = datetime.datetime.fromtimestamp(float(self.cleaned_data['delivery_date']))
        except ValueError:
            raise forms.ValidationError(_(u'The time does not have the required formatting, expected unixtime.'))
        return value

    def clean_remote_operator(self):
        # Get the operator, but do not die if this fails.
        try:
            oper, created = Operator.objects.get_or_create(entire_code=self.cleaned_data['remote_operator'])
        except AssertionError:
            return None
        return oper

    def clean_body_count(self):
        value = self.cleaned_data['body_count']
        if value is None:
            return 1
        return value

    def save(self):
        message = TextMessage.objects.create(
            status='in',
            local_address=self.cleaned_data['local_address'],
            remote_address=self.cleaned_data['remote_address'],
            remote_operator=self.cleaned_data['remote_operator'],
            body=self.cleaned_data['body'],
            body_count=self.cleaned_data['body_count'],
            delivery_date=self.cleaned_data['delivery_date'],
        )
        if self.cleaned_data['id'] != None:
            TextMessageExtra.objects.create(textmessage=message, foreign_reference=str(self.cleaned_data['id']))
        incoming_message.send(sender=TextMessage, instance=message, appended=False)
        return message


class DeliveryReportForm(forms.Form):
    '''
    The SMS gateway calls this for delivery report of outbound text
    messages.
    '''
    id = forms.IntegerField(help_text=_(u'The message identifier.'))
    acks = forms.IntegerField(help_text=_(u'How many parts of this message were delivered properly.'))
    naks = forms.IntegerField(help_text=_(u'How many parts of this message were NOT delivered properly.'))
    pnds = forms.IntegerField(help_text=_(u'How many parts of this message are still pending.'))
    # XXX we may want to add some more than just id and status: some extra validity checks? status messages?

    def __init__(self, *args, **kwargs):
        if 'data' in kwargs:
            log('data: %r' % kwargs['data'], log='sms', subsys='zjipz-dlr', fail_silently=True)
        elif len(args) > 0:
            log('data: %r' % args[0], log='sms', subsys='zjipz-dlr', fail_silently=True)
        super(DeliveryReportForm, self).__init__(*args, **kwargs)

    def clean_id(self):
        try:
            value = TextMessage.objects.get(extra__foreign_reference=self.cleaned_data['id'])
            assert value.status in ('out', 'pnd', 'ack', 'nak')
        except (AssertionError, TextMessage.DoesNotExist):
            raise forms.ValidationError(_(u'Message not found.'))
        return value

    def clean_acks(self):
        value = self.cleaned_data['acks']
        if not (0 <= value <= 15):
            raise forms.ValidationError(_(u'Unrealistic count.'))
        return value

    def clean_naks(self):
        value = self.cleaned_data['naks']
        if not (0 <= value <= 15):
            raise forms.ValidationError(_(u'Unrealistic count.'))
        return value

    def clean_pnds(self):
        value = self.cleaned_data['pnds']
        if not (0 <= value <= 15):
            raise forms.ValidationError(_(u'Unrealistic count.'))
        return value

    def clean(self):
        if len(set(self.cleaned_data.keys()).intersection(['acks', 'naks', 'pnds'])) == 3:
            body_count = self.cleaned_data['acks'] + self.cleaned_data['naks'] + self.cleaned_data['pnds']
            if not (1 <= body_count <= 15):
                raise forms.ValidationError(_(u'Unrealistic count.'))
        return self.cleaned_data

    def save(self):
        # Get the message by reference; we've already checked it in
        # clean().
        message = self.cleaned_data['id']
        acks, naks, pnds = self.cleaned_data['acks'], self.cleaned_data['naks'], self.cleaned_data['pnds']
        if acks:
            message.status = 'ack'
            message.body_count = acks # ok.. this is cheating, but calculation of profit does not break
        elif pnds:
            message.status = 'pnd'
            message.body_count = acks + naks + pnds
        else:
            message.status = 'nak'
            message.body_count = acks + naks + pnds
        message.delivery_date = datetime.datetime.now()
        message.save()
        return message
