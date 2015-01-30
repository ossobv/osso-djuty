# vim: set ts=8 sw=4 sts=4 et ai:
from django.template.loader import get_template
from django.template import Context
from django.contrib.sites.models import Site
try:
    from django.utils.encoding import force_text
except ImportError:
    from django.utils.encoding import force_unicode as force_text
from django.utils.translation import ugettext_lazy as _

def sender_notification(invite, notification_string):
    #Send mail to meeting sender that the member has accepted the meeting
    sender_email_address = invite.meeting.email_address or invite.meeting.user.email
    site = Site.objects.get_current()
    context = Context({
            'sender_name': invite.meeting.name,
            'invited_name': invite.member.name,
            'date': invite.meeting.date,
            'time': invite.meeting.time,
            'notification_string': notification_string,
            'site': site,
            'site_name': site.name,
            'site_domain': site.domain,
        }
    )
    html_template = get_template('meeting/mail/sender_invite_notification.html')
    plain_template = get_template('meeting/mail/sender_invite_notification.txt')

    from osso.cms.meeting.models import EmailMessage
    email = EmailMessage.objects.create(
        email_address = sender_email_address,
        subject = force_text(_('Invitation %(notification_string)s by %(name)s') % {'notification_string': notification_string, 'name': invite.member.name}),
        plain = plain_template.render(context),
        html = html_template.render(context),
    )
    email.send()
