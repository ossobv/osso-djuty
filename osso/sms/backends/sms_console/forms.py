# vim: set ts=8 sw=4 sts=4 et ai:
# We won't work on ancient (32-bit) systems where int!=long and 32 bits
# is the max integer.  Either use 64-bit or a newer python.  We need
# this check, because 0xffffffffL ('L') doesn't work anymore in
# python3.  We also remove the calls to long() in favor of calls to
# int() because the former is gone in python3.
if 0xffffffff == -1:
    raise NotImplementedError()

import datetime
import time
from django import forms
from django.utils.translation import ugettext_lazy as _
from osso.sms.models import Operator, TextMessage
from osso.sms.signals import incoming_message


def now():
    return int(time.time())


class IncomingTextMessageForm(forms.Form):
    '''
    The SMS gateway calls this for incoming text messages.
    '''
    shortcode = forms.CharField(max_length=32, initial='4411',
        help_text=_('The shortcode that the text message was sent to.'))
    keyword = forms.CharField(max_length=64, initial='EXAMPLE',
        required=False, help_text=_('The keyword used.'))
    message = forms.CharField(max_length=2048, initial='EXAMPLE hello world',
        help_text=_('The full message (including the keyword).'))
    originator = forms.CharField(max_length=32, initial='31612345678',
        help_text=_('The remote phone number.'))
    operator = forms.CharField(max_length=32, required=False, initial='20408',
        help_text=_('Mobile operator code (e.g. "20408" for KPN Telecom).'))
    receive_timestamp = forms.IntegerField(initial=now,
        help_text=_('Time the message was received by the operator.'))

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
        if (any(i not in '0123456789' for i in value) or
                len(value) == 0 or value[0] == '0'):
            raise forms.ValidationError(_('Expected phone number to be clean '
                                          'and complete.'))
        return '+%s' % value

    def clean_receive_timestamp(self):
        try:
            value = int(self.cleaned_data['receive_timestamp'])
            assert 946684800 <= value < 4102444800  # between Y 2000 and 2100
            value = datetime.datetime(*time.localtime(value)[:6])
        except (AssertionError, ValueError):
            raise forms.ValidationError(_('The time does not have the '
                                          'required formatting, expected '
                                          'a unix timestamp.'))
        return value

    def save(self):
        # Combine keyword with shortcode/destination to form the local
        # address.
        keyword = self.cleaned_data['keyword'].upper()
        local_address = ('%s %s' %
                         (self.cleaned_data['shortcode'], keyword)).strip()

        # Strip body of the optional keyword.
        body = self.cleaned_data['message'].lstrip()
        if body[:len(keyword)].upper() == keyword:
            body = body[len(keyword):].lstrip()

        message = TextMessage.objects.create(
            status='in',
            local_address=local_address,
            remote_address=self.cleaned_data['originator'],
            remote_operator=self.cleaned_data['operator'],
            body=body,
            delivery_date=self.cleaned_data['receive_timestamp'],
        )
        incoming_message.send(sender=TextMessage, instance=message,
                              appended=False)
        return message
