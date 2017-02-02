# vim: set ts=8 sw=4 sts=4 et ai:
import re

from django.db import models
from django.db.models.signals import post_syncdb
from django.utils.translation import ugettext_lazy as _

from osso.core import pickle
from osso.core.db import enumify
from osso.core.models import (
    Model, DecimalField, PhoneNumberField, SafeCharField)
from osso.relation.models import Country
from osso.sms import DestinationError
from osso.sms.manager import OperatorManager, TextMessageManager


STATUS_CHOICES = (
    ('in', _('Inbound')),               # unread
    ('rd', _('Inbound read')),          # read
    ('out', _('Outbound')),             # not sent
    ('pnd', _('Outbound pending')),     # sent and waiting
    ('nak', _('Outbound failed')),      # sent unsuccessfully
    ('ack', _('Outbound sent')),        # sent succesfully
)

BLANK_RE = re.compile(r'\s+')
NON_ALNUM_RE = re.compile(r'[^0-9A-Za-z]+')


class OperatorCountryCode(models.Model):
    '''
    The GSM operator country code.

    E.g. 204 for the Netherlands.
    '''
    if Country:
        country = models.OneToOneField(Country, primary_key=True,
            help_text=_('The country.'))
    else:
        country = models.CharField(max_length=2, primary_key=True,
            help_text=_('Two letter country code.'))
    code = models.PositiveIntegerField(db_index=True,
        help_text=_('A three digit GSM country code.'))

    def __unicode__(self):
        return u'%s (%s)' % (self.country, self.code)

    class Meta:
        if Country:
            ordering = ('country__name',)
        else:
            ordering = ('country',)


class Operator(Model):
    '''
    A GSM operator.

    E.g. KPN Telecom (204-08) in the Netherlands.
    '''
    if Country:
        country = models.ForeignKey(Country,
            help_text=_('The country (found through the first part '
                        'of the code).'))
    else:
        country = models.CharField(max_length=2,
            help_text=_('Two letter country code.'))
    code = models.PositiveIntegerField(
        help_text=_('The GSM operator code, e.g. 8 for 204-08 KPN Telecom.'))
    name = SafeCharField(max_length=64, blank=True,
        help_text=_('A friendly name, e.g. "KPN Telecom".'))

    objects = OperatorManager()

    def entire_code(self, separator='-'):
        return '%3d%s%02d' % (OperatorCountryCode.objects.get(country=self.country).code, separator, self.code)

    if Country:
        def __unicode__(self):
            return u'%s %s (%s)' % (self.entire_code(), self.name, self.country.code)
    else:
        def __unicode__(self):
            return u'%s %s (%s)' % (self.entire_code(), self.name, self.country)

    class Meta:
        unique_together = ('code', 'country')


class TextMessage(models.Model):
    '''
    A text message of the short message service (SMS) kind.

    If you need to store more information, use a one2one mapping that
    stores e.g. whether you're done with the message or who owns the
    message an so on.
    '''
    created = models.DateTimeField(auto_now_add=True, db_index=True,
        help_text=_('When the text message was created in this system.'))
    modified = models.DateTimeField(auto_now=True,
        help_text=_('When the text message was last modified.'))
    status = models.CharField(choices=STATUS_CHOICES,
        max_length=max(len(i[0]) for i in STATUS_CHOICES),
        help_text=_('The status of the message (includes direction).'))
    local_address = SafeCharField(max_length=32, blank=True,
        help_text=_('Local phone number. This does not necessarily '
                    'need to be a phone number.'))
    remote_address = PhoneNumberField(
        help_text=_('The phone number of the remote end: the originator '
                    'on inbound and the recipient on outbound '
                    '(with country code, without leading zeroes).'))
    remote_operator = models.ForeignKey(Operator, blank=True, null=True,
        help_text=_('Optionally the GSM operator of the remote end.'))
    body = models.TextField(
        help_text=_('The message body. In case of a simple messaging '
                    'server, this should be at most 160 characters long.'))
    body_count = models.PositiveIntegerField(default=1,
        help_text=_('How many messages this message is composed of.'))  # could be important for reply counts or billing purposes
    delivery_date = models.DateTimeField(blank=True, null=True, db_index=True,
        help_text=_('The delivery date. On an outbound message, this '
                    'should be set first on acknowledgement of receipt.'))
    metadata = models.TextField(blank=True,
        help_text=_('Optional metadata as a pickled python object. By '
                    'convention this is either None or a list of '
                    'dictionaries.'))

    objects = TextMessageManager()

    def __init__(self, *args, **kwargs):
        self.connection = kwargs.pop('connection', None)
        super(TextMessage, self).__init__(*args, **kwargs)

    def _meta_read(self):
        if self.metadata == '':
            return None
        # Python pickle routines using protocol 0 use both low and high
        # bytestring characters (<0x20 and >0x7f). We could do
        #   return pickle.loads(self.metadata.encode('latin1'))
        # here and
        #   self.metadata = pickle.dumps(value).decode('latin1')
        # in _meta_write. (latin1 is just an example, any encoding that
        # uses the all 8bit characters is fine.) But then we still get
        # the low ascii which is fragile in browser textboxes.
        #
        # See python issue http://bugs.python.org/issue2980 for the
        # >0x7f part of the issue.
        return pickle.loadascii(self.metadata)

    def _meta_write(self, value):
        if value in (None, ''):
            self.metadata = ''
        else:
            self.metadata = pickle.dumpascii(value)

    def _meta_delete(self):
        self.metadata = ''
    meta = property(_meta_read, _meta_write, _meta_delete, 'Get or set freeform metadata.')

    def meta_append(self, dict_or_none, commit=True):
        '''
        Append a dictionary to the metadata. If dict_or_none is None,
        nothing is appended. Note that the object is saved anyway if
        commit is True.
        '''
        if dict_or_none is not None:
            meta = self.meta
            if meta is None:
                meta = [dict_or_none]
            else:
                assert isinstance(meta, list), 'Expected meta to be a list of dictionaries, not %r.' % meta
                meta.append(dict_or_none)
            self.meta = meta
        if commit:
            self.save()

    def create_reply(self, body):
        return TextMessage.objects.create(
            status='out',
            local_address=self.local_address.split(' ', 1)[0],  # use only shortcode, not any keywords
            remote_address=self.remote_address,
            remote_operator=self.remote_operator,
            body=body
        )

    def get_connection(self, fail_silently=False):
        from osso.sms import get_connection
        if not self.connection:
            self.connection = get_connection(fail_silently=fail_silently)
        return self.connection

    def get_keywords(self, max_keywords, mode='loose'):
        '''
        Get the N keywords starting at the shortcode, moving on to the
        words in the SMS body. Yes, get_keywords(1)[0] is the shortcode!

        Observe that we ignore the keywords supplied by the provider. If
        you want to use that, you can get it from the local_address, but
        in most cases these keywords are still in the message body.

        This is the preferred way to match messages by keyword, as
        upstream providers may or may not know about your particular
        keyword, so checking the local_address will probably not be
        enough.

        Keywords returned from here are guaranteed to be in [0-9A-Z].

        The mode flag can be one of 'loose', 'normal', 'strict'. They
        separate the keywords by '\\W+', '\\s+' and ' ' respectively.

        >>> from osso.sms.models import TextMessage
        >>> t = TextMessage(local_address='1008 X', body="i -wouldn't  t99")
        >>> t.get_keywords(0)
        []
        >>> t.get_keywords(1)
        ['1008']
        >>> t.get_keywords(2)
        ['1008', 'I']
        >>> t.get_keywords(3)
        ['1008', 'I', 'WOULDN']
        >>> t.get_keywords(4)
        ['1008', 'I', 'WOULDN', 'T']
        >>> t.get_keywords(5)
        ['1008', 'I', 'WOULDN', 'T', 'T99']
        >>> t.get_keywords(6)
        ['1008', 'I', 'WOULDN', 'T', 'T99']

        >>> t = TextMessage(local_address='1008', body=" i    -wouldn't  t99")
        >>> t.get_keywords(3, mode='loose')
        ['1008', 'I', 'WOULDN']
        >>> t.get_keywords(3, mode='normal')
        ['1008', 'I', "-WOULDN'T"]
        >>> t.get_keywords(3, mode='strict')
        ['1008', '', 'I']

        >>> t = TextMessage(local_address='1008', body="\\n\\r\\t\\v pleenty\\tspace\\n\\r\\t\\v ")
        >>> t.get_keywords(4, mode='loose')
        ['1008', 'PLEENTY', 'SPACE']
        >>> t.get_keywords(4, mode='normal')
        ['1008', 'PLEENTY', 'SPACE']

        >>> t = TextMessage(local_address='1008 STOP', body="stop")
        >>> t.get_keywords(3)
        ['1008', 'STOP']
        >>> t = TextMessage(local_address='1008', body="sToP!!.@")
        >>> t.get_keywords(3)
        ['1008', 'STOP']

        Test the non-loose (sloppy) modes.

        >>> t = TextMessage(local_address='1008 X', body="i -wouldn't  t99 ")
        >>> t.get_keywords(0, mode='normal'), t.get_keywords(0, mode='strict')
        ([], [])
        >>> t.get_keywords(1, mode='normal'), t.get_keywords(1, mode='strict')
        (['1008'], ['1008'])
        >>> t.get_keywords(3, mode='normal'), t.get_keywords(3, mode='strict')
        (['1008', 'I', "-WOULDN'T"], ['1008', 'I', "-WOULDN'T"])
        >>> t.get_keywords(4, mode='normal')
        ['1008', 'I', "-WOULDN'T", 'T99']
        >>> t.get_keywords(4, mode='strict')
        ['1008', 'I', "-WOULDN'T", '']
        >>> t.get_keywords(9, mode='normal')
        ['1008', 'I', "-WOULDN'T", 'T99']
        >>> t.get_keywords(9, mode='strict')
        ['1008', 'I', "-WOULDN'T", '', 'T99', '']

        >>> t = TextMessage(local_address='1008', body="sToP!!.@")
        >>> t.get_keywords(3, mode='normal'), t.get_keywords(3, mode='strict')
        (['1008', 'STOP!!.@'], ['1008', 'STOP!!.@'])
        '''
        assert mode in ('loose', 'normal', 'strict')
        assert max_keywords >= 0

        if max_keywords == 0:
            return []

        shortcode = self.local_address.split(' ')[0]
        if max_keywords == 1:
            return [shortcode]
        if mode == 'strict':
            tmp = self.body.split(' ', max_keywords - 1)[0:(max_keywords - 1)]
            return [shortcode] + [i.upper() for i in tmp]
        split_re = (NON_ALNUM_RE, BLANK_RE)[mode == 'normal']
        return (
            [shortcode] + [i.upper() for i in split_re.split(self.body) if i != '']
        )[0:max_keywords]

    @property
    def is_inbound(self):
        return not self.is_outbound

    @property
    def is_outbound(self):
        return self.status not in ('in', 'rd')

    def send(self, reply_to=None, shortcode_keyword=None, tariff_cent=None, fail_silently=False):
        '''
        Send out the message. Don't call this unless you're prepared to
        wait a while and prepared to handle errors. See the sms
        management command for a sample sms sending cron job.
        '''
        # XXX: hope that we can obsolete reply_to, shortcode_keyword,
        # tariff_cent and have everyone use TextMessageExtra for that
        # purpose.
        assert self.pk is not None, 'Attempting to a send a message without a primary key.'
        assert self.status == 'out', 'Attempting to a send a message that is not in state outbound-unsent.'
        if not self.remote_address:
            if fail_silently:
                return 0
            else:
                raise DestinationError('Empty remote address')
        return self.get_connection(fail_silently).send_messages(
            [self],
            reply_to=reply_to,
            shortcode_keyword=shortcode_keyword,
            tariff_cent=tariff_cent
        )

    def __repr__(self):
        return 'TextMessage(id=%d)' % self.id

    def __str__(self):
        if self.status in ('in', 'rd'):
            return 'Inbound SMS from %s at %s' % (self.remote_address, self.created.strftime('%Y-%m-%d %H:%M'))
        else:
            return 'Outbound SMS to %s at %s' % (self.remote_address, self.created.strftime('%Y-%m-%d %H:%M'))

    class Meta:
        ordering = ('-id', 'remote_address')
        permissions = (
            ('view_textmessagestatus', 'Can view textmessage status'),
        )


class TextMessageExtra(models.Model):
    '''
    Model that contains SMS-provider specific information. The meta
    thing was a failed idea.

    Make sure you use a transactional database when using this for SMS
    sending. If you don't and you use a separate thread/process to
    empty your SMS queue, you might end up with messages sent for free
    because this object didn't exist yet when polling for new messages.
    '''
    textmessage = models.OneToOneField(TextMessage, related_name='extra',
            help_text=_('The textmessage that the extra info is about.'))
    shortcode = models.PositiveIntegerField(blank=True, null=True,
            help_text=_('Shortcode that this message was received on, or is sent from.'))
    keyword = SafeCharField(max_length=63, blank=True, null=True,
            help_text=_('Keyword that this message was received for, or is sent from.'))
    tariff_cent = models.PositiveIntegerField(default=0,
            help_text=_('Consumer price (MT) for sent SMS.'))
    foreign_reference = SafeCharField(max_length=31, blank=True, db_index=True,
            help_text=_('Foreign reference (e.g. mid for Mollie).'))
    foreign_status = SafeCharField(max_length=31, blank=True, default='',
            help_text=_('Same as status, but SMS-provider specific.'))

    @property
    def tariff(self):
        return float(self.tariff_cent) / 100

    def __str__(self):
        return 'SMS Info #%d @ %s %s \u00a4 %d (%s, %s)' % (
            self.textmessage_id, self.shortcode, self.keyword, self.tariff_cent, self.foreign_reference, self.foreign_status or '...'
        )


class Payout(Model):
    '''
    Payout contains the relation between the telecom operator, the
    shortcode, the MO/MT (Mobile Originated/Terminated) text message
    tariff and the payout to this business (which can be significantly
    lower than the tariff).
    '''
    operator = models.ForeignKey(Operator,
        help_text=_('The GSM operator.'))
    local_address = SafeCharField(max_length=32, blank=True,
        help_text=_('Local phone number, e.g. a shortcode. Leave empty to match all.'))
    tariff_cent = models.PositiveIntegerField(blank=True, null=True,
        help_text=_('The MT SMS tariff in cents. Leave NULL to set the MO payout. '
                    '(Watch out for dupes. The unique constraint will not work with NULL values.)'))
    payout_cent = DecimalField(
        help_text=_('The Payout (in cents!) by the GSM operator for this tariff.'))

    class Meta:
        unique_together = ('operator', 'local_address', 'tariff_cent')


# Alter choicefields to use an enum type
def _enumify_choices(sender=None, **kwargs):
    if sender.__name__ == 'osso.sms.models':
        enumify(TextMessage, 'status', (i[0] for i in STATUS_CHOICES))
post_syncdb.connect(_enumify_choices)
