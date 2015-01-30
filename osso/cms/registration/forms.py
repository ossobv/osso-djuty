from django import forms
from django.utils.translation import ugettext_lazy as _

from registration.forms import RegistrationFormUniqueEmail
from django.template.defaultfilters import slugify

class RegistrationForm(RegistrationFormUniqueEmail):
    username = forms.CharField(max_length=30, required=False, widget=forms.HiddenInput, label=_(u'Username'))
    email = forms.EmailField(max_length=75, label=_(u'E-mail address'))
    password1 = forms.CharField(widget=forms.PasswordInput(render_value=False), label=_(u'Password'))
    password2 = forms.CharField(widget=forms.PasswordInput(render_value=False), label=_(u'Password (again)'))

    def clean(self):
        cleaned_data = super(RegistrationForm, self).clean()
        if 'email' in cleaned_data and cleaned_data['email'] is not ('', None):
            cleaned_data['username'] =  slugify(cleaned_data['email'][:30])
        return cleaned_data

class NewsletterRegistrationForm(RegistrationFormUniqueEmail):
    username = forms.CharField(max_length=30, required=False, widget=forms.HiddenInput, label=_(u'Username'))
    name = forms.CharField(max_length=30, required=False, label=_('Name'))
    email = forms.EmailField(max_length=75, label=_(u'E-mail address'))
    password1 = forms.CharField(widget=forms.PasswordInput(render_value=False), label=_(u'Password'))
    password2 = forms.CharField(widget=forms.PasswordInput(render_value=False), label=_(u'Password (again)'))

    newsletter = forms.BooleanField(widget=forms.CheckboxInput(),
                                    label=_('Keep me informed of new services'),
                                    required=False)

    tos = forms.BooleanField(widget=forms.CheckboxInput(),
                             label=_(u'I have read and agree to the Terms of Service'),
                             error_messages={ 'required': u"You must agree to the terms to register" })
    #Houd mij op de hoogte van nieuwe diensten van EasyConference

    def clean(self):
        cleaned_data = super(NewsletterRegistrationForm, self).clean()
        if 'email' in cleaned_data and cleaned_data['email'] is not ('', None):
            cleaned_data['username'] =  slugify(cleaned_data['email'][:30])
        return cleaned_data

    class Meta:
        fieldsets = (
            (None, {'fields': ('name', 'email', 'password1', 'password2', 'newsletter', 'tos',)}),
        )
