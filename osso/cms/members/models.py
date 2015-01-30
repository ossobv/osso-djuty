from django.db import models
from django.contrib.auth.models import User
from django.utils.translation import ugettext_lazy as _

from osso.core.models.fields import PhoneNumberField

class Group(models.Model):
    user = models.ForeignKey(User)
    name = models.CharField(max_length=25)

    def __unicode__(self):
        return self.name

class Member(models.Model):
    group = models.ManyToManyField(Group, related_name='members', null=True, blank=True)
    user = models.ForeignKey(User, null=True, blank=True)
    name = models.CharField(max_length=25, blank=True, verbose_name=_('Name'), help_text=_('The name of the member.'))
    email_address = models.EmailField(blank=True, help_text=_('E-mail address of the member.'))
    phone_number = PhoneNumberField(blank=True, help_text=_('Phone number of the member.'))

    def __unicode__(self):
        return u'%s <%s>' % (self.name, self.email_address)
