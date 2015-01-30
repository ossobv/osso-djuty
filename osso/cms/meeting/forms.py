import datetime

from django import forms
from django.forms.models import modelformset_factory, BaseModelFormSet
from django.conf import settings
from django.utils.safestring import mark_safe
from django.utils.translation import ugettext_lazy as _


from osso.cms.meeting.models import Meeting
from osso.cms.members.models import Member
from osso.cms.meeting.widgets import SelectDateWidget, SelectTimeWidget
from captcha.fields import CaptchaField

class DateWidget(SelectDateWidget):
    def render(self, name, value, attrs=None):
        output = super(DateWidget, self).render(name, value, attrs)
        return mark_safe(output + ' <span class="DateField"></span>')

    class Media:
        js = (settings.MEDIA_URL + 'js/jquery-ui-1.7.2.custom.min.js',
              settings.MEDIA_URL + 'js/DateTime.js',)
        css = {'screen': (settings.MEDIA_URL + 'smoothness/jquery-ui-1.7.2.custom.css',)}

CAPTCHA_ERROR_MESSAGES = {'invalid': _('The characters you entered didn\'t match the characters verification. Please try again.'),}

class InviteForm(forms.ModelForm):
    date = forms.DateField(widget=DateWidget, label=_('Date'), initial=datetime.date.today, help_text=_('Date of meeting'))
    time = forms.TimeField(widget=SelectTimeWidget, label=_('Time'), initial=lambda: datetime.datetime.now().time(), help_text=_('Time of meeting'))
    captcha = CaptchaField(error_messages=CAPTCHA_ERROR_MESSAGES)

    def __init__(self, *args, **kwargs):
        self.groups = kwargs.pop('groups')
        super(InviteForm, self).__init__(*args, **kwargs)

    def clean_date(self, **kwargs):
        date = self.cleaned_data['date']
        if date < datetime.date.today():
            raise forms.ValidationError(_('The date of a meeting can\'t be in the past.'))
        return date

    class Meta:
        model = Meeting
        exclude = ('group','user')

class InviteGroupForm(InviteForm):
    group_text = forms.CharField(required=False)

    def __init__(self, *args, **kwargs):
        super(InviteGroupForm, self).__init__(*args, **kwargs)
        self.fields['group'].queryset = self.groups

    class Meta(InviteForm.Meta):
        exclude = ('user', 'email_address',)

class MemberForm(forms.ModelForm):
    def clean(self):
        cleaned_data = super(MemberForm, self).clean()
        if 'email_address' in cleaned_data \
                and cleaned_data['email_address'] in (None, '') \
                and 'phone_number' in cleaned_data \
                and cleaned_data['phone_number'] in (None, ''):
            raise forms.ValidationError(_('An e-mail address or a mobile phonenumber should be entered.'))
        return cleaned_data

    class Meta:
        model = Member

MeetingInvitationPeopleForm = modelformset_factory(Member, form=MemberForm, exclude=('group','user',), extra=10, can_delete=False)
