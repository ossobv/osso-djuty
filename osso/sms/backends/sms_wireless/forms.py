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
import urllib2

from django import forms
from django.core.mail import mail_admins
from django.utils.translation import ugettext_lazy as _
from osso.sms.models import Operator, TextMessage
from osso.sms.signals import incoming_message
from osso.sms.backends.sms_wireless.models import (
    DeliveryReportForward, DeliveryReportForwardLog)


def now():
    return int(time.time())


class IncomingTextMessageForm(forms.Form):
    '''
    The SMS gateway calls this for incoming text messages.

    SMS messages with a body longer then 160 chars are sent:
     * in one request if the concatenation information is supplied by
       the operator
     * only the first part if the concatenation information is not
       supplied by the operator additional parts are not sent because
       they will not match our keyword

    POST = {
        DCS: '0',
        DEST: '4411',
        KEYWORD: 'TEST',
        MSG: 'Test message',
        OPR: '20404',
        ORIG: '31621803413',
        PID: '0',
        TIME: '1169129378',
        TYPE: 'sms',
        UNIQUEID: '432f98dcad3e373cde9a5b0acfacca36f341516f',
        VERSION: '1.1',
    }
    '''
    DEST = forms.CharField(max_length=32, initial='4411',
        help_text=_('The shortcode that the text message was sent to.'))
    KEYWORD = forms.CharField(max_length=64, initial='EXAMPLE', required=False,
        help_text=_('The keyword used.'))
    MSG = forms.CharField(max_length=2048, initial='example hello world',
        help_text=_('The full message (including the keyword).'))
    ORIG = forms.CharField(max_length=32, initial='31612345678',
        help_text=_('The remote phone number.'))
    OPR = forms.CharField(max_length=32, required=False, initial='20408',
        help_text=_('Mobile operator code (e.g. "20408" for KPN Telecom).'))
    TIME = forms.IntegerField(initial=now,
        help_text=_('Time the message was received by the operator.'))
    UNIQUEID = forms.CharField(max_length=64, required=False,
        help_text=_('The Wireless message ID.'))
    TYPE = forms.CharField(max_length=32, required=False, initial='sms',
        help_text=_('The request type.'))
    DCS = forms.IntegerField(min_value=0, max_value=255, initial=0,
        help_text=_('The data coding scheme.'))
    PID = forms.IntegerField(min_value=0, max_value=255, initial=0,
        help_text=_('The protocol identifier.'))

    def clean_OPR(self):
        # Get the operator, but do not die if this fails.
        try:
            oper, created = Operator.objects.get_or_create(
                entire_code=self.cleaned_data['OPR'])
        except AssertionError:
            return None
        return oper

    def clean_ORIG(self):
        value = self.cleaned_data['ORIG'].strip()
        if (any(i not in '0123456789' for i in value) or len(value) == 0 or
                value[0] == '0'):
            raise forms.ValidationError(_('Expected phone number to be '
                                          'clean and complete.'))
        return '+%s' % value

    def clean_TIME(self):
        try:
            value = int(self.cleaned_data['TIME'])
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
        keyword = self.cleaned_data['KEYWORD'].upper()
        local_address = ('%s %s' %
                         (self.cleaned_data['DEST'], keyword)).strip()

        # Remove excess whitespace from keyword.
        body = self.cleaned_data['MSG'].lstrip()
        if body[:len(keyword)].upper() == keyword:
            body = body[len(keyword):].lstrip()

        # Data for which the TextMessage object has no properties goes
        # in the meta property.
        meta = {
            'wireless_id': self.cleaned_data['UNIQUEID'],
            'wireless_type': self.cleaned_data['TYPE'],
            'wireless_pid': self.cleaned_data['PID'],
            'wireless_dcs': self.cleaned_data['DCS'],
        }

        message = TextMessage.objects.create(
            status='in',
            local_address=local_address,
            remote_address=self.cleaned_data['ORIG'],
            remote_operator=self.cleaned_data['OPR'],
            body=body,
            delivery_date=self.cleaned_data['TIME'],
            meta=[meta]
        )
        incoming_message.send(sender=TextMessage, instance=message,
                              appended=False)
        return message


class DeliveryReportForm(forms.Form):
    '''
    The SMS gateway calls this for delivery report of outbound text
    messages.

    POST = {
        BATCH: '1169129373342782',
        ORIG: '31621803413',
        SENT: '1169129373',
        STATUS: '200',
        TEXT: 'delivered',
        TIME: '1169129378',
        TYPE: 'sms-report',
        UNIQUEID: '432f98dcad3e373cde9a5b0acfacca36f341516f',
        VERSION: '1.1',
    }
    '''
    BATCH = forms.CharField(max_length=64,
        help_text=_('The message batch identifier.'))
    STATUS = forms.IntegerField(initial=200,
        help_text=_('The status code.'))
    ORIG = forms.CharField(max_length=32, initial='31612345678',
        help_text=_('The remote phone number.'))
    SENT = forms.IntegerField(initial=(lambda: '%d' % time.time()),
        help_text=_('The timestamp the message was sent.'))
    TIME = forms.IntegerField(initial=(lambda: '%d' % time.time()),
        help_text=_('The timestamp the message was delivered.'))
    UNIQUEID = forms.CharField(max_length=64, required=False,
        help_text=_('The Wireless message ID.'))
    TYPE = forms.CharField(max_length=32, required=False, initial='sms-report',
        help_text=_('The request type.'))
    TEXT = forms.CharField(max_length=64, required=False, initial='delivered',
        help_text=_('The status string.'))

    def clean_BATCH(self):
        value = self.cleaned_data['BATCH'].strip()
        try:
            value = TextMessage.objects.get(id=int(value.rsplit('-', 1)[-1]))
        except (IndexError, ValueError, TextMessage.DoesNotExist):
            raise forms.ValidationError(_('Batch not found.'))
        return value

    def clean_ORIG(self):
        value = self.cleaned_data['ORIG'].strip()
        if (any(i not in '0123456789' for i in value) or len(value) == 0 or
                value[0] == '0'):
            raise forms.ValidationError(_('Expected phone number to be '
                                          'clean and complete.'))
        return '+%s' % value

    def clean_SENT(self):
        try:
            self.cleaned_data['SENT'] = datetime.datetime(
                *time.localtime(self.cleaned_data['SENT'])[:6])
        except ValueError:
            raise forms.ValidationError(_('The time does not have the '
                                          'required formatting, expected '
                                          'a unix timestamp.'))
        return self.cleaned_data['SENT']

    def clean_TIME(self):
        try:
            self.cleaned_data['TIME'] = datetime.datetime(
                *time.localtime(self.cleaned_data['TIME'])[:6])
        except ValueError:
            raise forms.ValidationError(_('The time does not have the '
                                          'required formatting, expected '
                                          'a unix timestamp.'))
        return self.cleaned_data['TIME']

    def clean(self):
        # Double check: compare the message state and recipient
        message = self.cleaned_data.get('BATCH')
        if message and (message.remote_address != self.cleaned_data['ORIG'] or
                        message.status in ('in', 'ack', 'nak')):
            raise forms.ValidationError(_('Batch, recipient or status '
                                          'mismatch.'))
        return self.cleaned_data

    def save(self):
        # Get the message by reference; we've already checked it in
        # clean().
        message = self.cleaned_data['BATCH']

        # Set message status. We only receive notifications for
        # delivery success and delivery failure. 200 means delivered,
        # anything else means failure.
        if self.cleaned_data['STATUS'] == 200:
            message.status = 'ack'  # success
        else:
            message.status = 'nak'  # failed
        message.delivery_date = self.cleaned_data['TIME']

        # Add additional info to the metadata.
        meta = {
            'wireless_id': self.cleaned_data['UNIQUEID'],
            'wireless_type': self.cleaned_data['TYPE'],
            'wireless_sent': self.cleaned_data['SENT'],
            'wireless_status': self.cleaned_data['STATUS'],
            'wireless_status_str': self.cleaned_data['TEXT'],
        }
        message.meta_append(meta, commit=False)

        message.save()
        return message


class DeliveryReportForwardForm(forms.Form):
    '''
    The SMS gateway calls this for delivery report of outbound text
    messages. We use this form to forward a delivery report to the
    configured destination based on BATCH prefix filtering.
    '''
    BATCH = forms.CharField(max_length=64,
        help_text=_('The message batch identifier.'))

    def clean_BATCH(self):
        value = self.cleaned_data['BATCH'].strip()
        return value.rsplit('-', 1)[0]

    def clean(self):
        # store the batch_prefix in case the form is invalid
        self.batch_prefix = self.cleaned_data.get('BATCH')
        try:
            self.dlr_forward = DeliveryReportForward.objects.get(
                batch_prefix=self.batch_prefix)
        except DeliveryReportForward.DoesNotExist:
            raise forms.ValidationError(_('No forward available for this '
                                          'batch prefix.'))
        return self.cleaned_data

    def forward(self, request):
        assert not self.errors, ('Can not forward the delivery report '
                                 'because the data did not validate.')
        post_data = request.POST.urlencode()
        destination = self.dlr_forward.destination
        try:
            f = urllib2.urlopen(destination, post_data)
            response = f.read()
            f.close()
        except Exception as e:
            response = repr(e)
        log = DeliveryReportForwardLog.objects.create(
            batch_prefix=self.batch_prefix,
            post_data=post_data,
            destination=destination,
            response=response,
        )
        # response does not match the wireless format
        # notify the admins and mark the report as accepted
        if not response.startswith(u'[RESPONSE'):
            self.mail_admins(log)
            return u'[RESPONSE-OK]'
        return response

    def log(self, request):
        log = DeliveryReportForwardLog.objects.create(
            batch_prefix=self.batch_prefix,
            post_data=request.POST.urlencode(),
            destination='Unknown',
            response=('Unknown batch prefix, accepted message and returned OK '
                      'response'),
        )
        self.mail_admins(log)

    def mail_admins(self, log):
        mail_admins(
            u'Unable to forward delivery report',
            (u'DLR Log ID: %d\nBatch prefix: %s\nDestination: %s\n'
             u'Response: %s\nPOST: %s') %
            (log.pk, log.batch_prefix, log.destination, log.response,
             log.post_data),
            fail_silently=True,
        )
