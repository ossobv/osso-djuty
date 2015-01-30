# vim: set ts=8 sw=4 sts=4 et ai:
import datetime

from django.conf import settings
from django.db import models
from django.core.urlresolvers import reverse
from django.core.mail import EmailMultiAlternatives
from django.contrib.auth.models import User
from django.contrib.sites.models import Site
from django.utils.translation import ugettext_lazy as _
try:
    from django.utils.encoding import force_text
except ImportError:
    from django.utils.encoding import force_unicode as force_text
from django.template.loader import get_template
from django.template import Context
from email.MIMEImage import MIMEImage

from osso.cms.members.models import Group, Member
from osso.cms.meeting.utils import sender_notification
from osso.sms.models import TextMessage
from osso.sms.signals import incoming_message


class Message(models.Model):
    created = models.DateTimeField(auto_now_add=True)
    delivered = models.DateTimeField(blank=True, null=True)

    class Meta:
        abstract = True


class EmailMessage(Message):
    email_address = models.EmailField()
    subject = models.CharField(max_length=128)
    plain = models.TextField()
    html = models.TextField()

    def send(self):
        email = EmailMultiAlternatives(subject=self.subject, body=self.plain,
                                       to=(self.email_address,))
        email.attach_alternative(self.html, mimetype='text/html')
        if hasattr(settings, 'MEETING_EMAIL_LOGO'):
            img_data = open(settings.MEETING_EMAIL_LOGO)
            logo = MIMEImage(img_data.read())
            logo.add_header('Content-ID', '<logo>')
            email.attach(logo)
            img_data.close()
        email.send()
        self.delivered = datetime.datetime.now()
        self.save()


class EmailStyling(models.Model):
    site = models.OneToOneField(Site, related_name='email_styling')
    style = models.TextField()

    def __unicode__(self):
        return self.style


class Meeting(models.Model):
    user = models.ForeignKey(User, null=True, blank=True)
    email_address = models.EmailField(verbose_name=_('E-mail address'),
        null=True, help_text=_('Enter your e-mail address.'))
    name = models.CharField(max_length=20, verbose_name=_('Name'),
        help_text=_('Enter your name.'))
    subject = models.CharField(max_length=25, null=True, blank=True,
        verbose_name=_('Subject'), help_text=_('Subject of meeting'))
    group = models.ForeignKey(Group, null=True, blank=True,
        verbose_name=_('Group'),
        help_text=_('Select a group or enter a name to create a new group.'))
    date = models.DateField(verbose_name=_('Date'),
        help_text=_('Date of meeting'))
    time = models.TimeField(verbose_name=_('Time'),
        help_text=_('Time of meeting'))
    pin_code = models.CharField(max_length=5,
        verbose_name=_('Access code'), help_text=_('Access code of meeting.'))

    @property
    def accepted_invites(self):
        return self.invites.filter(accept=True)

    @property
    def rejected_invites(self):
        return self.invites.filter(accept=False)

    def __unicode__(self):
        return u'%s %s %s' % (self.date, self.time, self.name)

    class Meta:
        ordering = ('-date', '-time',)


class Invite(models.Model):
    created = models.DateTimeField(auto_now_add=True)
    meeting = models.ForeignKey(Meeting, related_name='invites')
    member = models.ForeignKey(Member, related_name='members')
    accept = models.NullBooleanField()
    token = models.CharField(max_length=16)

    def save(self, *args, **kwargs):
        if not self.id:
            is_new = True
        else:
            is_new = False
        super(Invite, self).save(*args, **kwargs)
        if is_new:
            self.send()

    def send(self):
        assert self.pk is not None, \
            'Attempting to a send an invitation without a primary key.'
        assert self.accept is None, \
            ('Attempting to a send an invitation which has been '
             'declined/confirmed.')

        if self.member.email_address:
            site = Site.objects.get_current()
            context = Context({
                'name': self.meeting.name,
                'subject': self.meeting.subject,
                'date': self.meeting.date,
                'time': self.meeting.time,
                'phone_number': settings.MEETING_PHONE_NUMBER,
                'pin_code': self.meeting.pin_code,
                'site': site,
                'site_domain': site.domain,
                'site_name': site.name,
                'accept_url': reverse('meeting_invite_accept',
                                      args=[self.id, self.token]),
                'reject_url': reverse('meeting_invite_reject',
                                      args=[self.id, self.token]),
                'invite_name': self.member.name,
            })

            plain_mail = get_template('meeting/mail/mail.txt')
            html_mail = get_template('meeting/mail/mail.html')

            email = EmailMessage.objects.create(
                email_address=self.member.email_address,
                subject=force_text(_('You\'re invited')),
                plain=plain_mail.render(context),
                html=html_mail.render(context),
            )
            email.send()
        if self.member.phone_number:
            try:
                self.meeting.meetingtextmessage
            except MeetingTextMessage.DoesNotExist:
                sms_template = get_template('meeting/mail/text.txt')
            else:
                sms_template = get_template('meeting/mail/text_now.txt')

            sms_context = Context({
                'name': self.meeting.name,
                'date': self.meeting.date.strftime('%Y-%m-%d'),
                'time': self.meeting.time.strftime('%H:%M'),
                'phone_number': settings.MEETING_PHONE_NUMBER,
                'pin_code': self.meeting.pin_code,
                'keyword_confirm': settings.MEETING_SMS_KEYWORD_CONFIRM,
                'keyword_decline': settings.MEETING_SMS_KEYWORD_DECLINE,
                'shortcode': settings.MEETING_SMS_SHORTCODE,
            })

            if self.member.phone_number.startswith('+31'):
                local_address = settings.MEETING_SMS_ORIGINATOR
            else:
                local_address = (
                    settings.MEETING_SMS_INTERNATION_SMS_ORIGINATOR or
                    settings.MEETING_SMS_ORIGINATOR)

            sms = TextMessage.objects.create(
                status='out',
                local_address=local_address,
                remote_address=self.member.phone_number,
                body=(sms_template.render(sms_context)
                      .strip()[:settings.MEETING_SMS_MAX_LENGTH])
            )
            sms.send()
            InviteTextMessage.objects.create(invite=self, message=sms)


class InviteTextMessage(models.Model):
    invite = models.ForeignKey(Invite)
    message = models.OneToOneField(TextMessage)


class MeetingTextMessage(models.Model):
    meeting = models.OneToOneField(Meeting)
    message = models.OneToOneField(TextMessage)


def inbound_sms_callback(instance, **kwargs):
    # do we need to handle this message?
    if not (instance.local_address.endswith(' ' + settings.MEETING_SMS_KEYWORD_CONFIRM)
            or instance.local_address.endswith(' ' + settings.MEETING_SMS_KEYWORD_DECLINE)
            or instance.local_address.endswith(' ' + settings.MEETING_SMS_KEYWORD_SEND)):
        return

    if instance.local_address.endswith(' ' + settings.MEETING_SMS_KEYWORD_SEND):
        body_list = (instance.body.replace(',', ' ').replace('<', '')
                     .replace('>', '').split(' '))

        name_list = []
        s = body_list.pop(0)
        while not s.isdigit():
            name_list.append(s)
            s = body_list.pop(0)

        name = ' '.join(name_list)
        pin_code = s
        phone_numbers = body_list

        members = []
        for phone_number in phone_numbers:
            # Validate phone number
            if phone_number[0] == '+':
                phone_number = phone_number[1:]
            elif (len(phone_number) > 1 and phone_number[0] == '0' and
                  phone_number[1] == '0'):
                phone_number = phone_number[2:]
            elif (len(phone_number) > 1 and phone_number[0] == '0' and
                  phone_number[1] in '123456789'):
                phone_number = '%s%s' % ('31', phone_number[1:])
            else:
                continue

            if phone_number[0] == '0' or any(i not in '0123456789'
                                             for i in phone_number):
                continue

            members.append(Member.objects.create(phone_number=('+%s' %
                                                               phone_number)))

        if members:
            meeting = Meeting.objects.create(
                name=name,
                pin_code=pin_code,
                date=datetime.date.today(),
                time=datetime.datetime.now().time()
            )
            MeetingTextMessage.objects.create(meeting=meeting,
                                              message=instance)
            for member in members:
                Invite.objects.create(meeting=meeting, member=member)
        return

    # locate all matching invites which have not been confirmed or declined.
    # because the message does not have a reference we use a FIFO policy.
    invite_list = list(Invite.objects
                       .filter(member__phone_number=instance.remote_address,
                               accept=None).order_by('created'))
    if len(invite_list) == 0:
        return
    invite = invite_list[0]
    # store a reference to the invite
    InviteTextMessage.objects.create(invite=invite, message=instance)
    # mark the invite as confirmed or declined
    if instance.local_address.endswith(' ' + settings.MEETING_SMS_KEYWORD_CONFIRM):
        invite.accept = True
        sender_notification(invite, _('accepted'))
    elif instance.local_address.endswith(' ' + settings.MEETING_SMS_KEYWORD_DECLINE):
        invite.accept = False
        sender_notification(invite, _('not accepted'))
    invite.save()

incoming_message.connect(inbound_sms_callback)
