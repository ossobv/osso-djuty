from django import forms
from django.forms.util import ErrorList
from django.utils.translation import ugettext_lazy as _
from osso.core.forms.fields import PhoneNumberField
from osso.cms.members.models import Group, Member

class GroupForm(forms.ModelForm):
    class Meta:
        model = Group
        exclude = ('user',)

class MemberForm(forms.ModelForm):

    def __init__(self, *args, **kwargs):
        super(MemberForm, self).__init__(*args, **kwargs)
        self.fields['group'].help_text = None
        self.fields['group'].widget = forms.CheckboxSelectMultiple(attrs={},choices=self.fields['group'].widget.choices)

    class Meta:
        model = Member
        exclude = ('user',)

class MemberAddForm(forms.ModelForm):
    name = forms.CharField(required=False)
    email_address = forms.EmailField(required=False)
    phone_number = PhoneNumberField(required=False)
    other_members = forms.ModelChoiceField(Member.objects.all(), required=False)

    def __init__(self, *args, **kwargs):
        members_queryset = kwargs.pop('members')
        super(MemberAddForm, self).__init__(*args, **kwargs)
        self.fields['other_members'].queryset = members_queryset

    def clean(self):
        if 'other_members' in self.cleaned_data:
            if self.cleaned_data['other_members'] in (None, ''):
                if 'name' in self.cleaned_data and self.cleaned_data['name'] in (None, ''):
                    self.errors['name'] = ErrorList([_('This field is required.')])
                    del self.cleaned_data['name']
                if 'email_address'  in self.cleaned_data and self.cleaned_data['email_address'] in (None, ''):
                    self.errors['email_address'] = ErrorList([_('This field is required.')])
                    del self.cleaned_data['email_address']
        return self.cleaned_data

    def get_member(self, *args, **kwargs):
        if 'other_members' in self.cleaned_data and self.cleaned_data['other_members'] not in (None, ''):
            return self.cleaned_data['other_members']
        else:
            return self.save()

    class Meta:
        model = Member
        exclude = ('group','user')
