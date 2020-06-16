# vim: set ts=8 sw=4 sts=4 et ai:
from django import forms
from django.contrib.auth import authenticate
from django.contrib.auth.backends import ModelBackend
from django.contrib.auth.forms import AuthenticationForm
from django.utils.translation import gettext_lazy as _


__all__ = ('LowercaseUsernameModelBackend',
           'LowercaseAuthenticationForm')


class LowercaseUsernameModelBackend(ModelBackend):
    def authenticate(self, username=None, password=None):
        return (super(LowercaseUsernameModelBackend, self)
                .authenticate(username.lower(), password))


class LowercaseAuthenticationForm(AuthenticationForm):
    __errmsg = {
        'incorrect': _('Please enter a correct username and password. The '
                       'password is case sensitive.'),
        'inactive': _('This account is inactive.'),
    }

    def clean_username(self):
        return self.cleaned_data['username'].lower()

    def clean(self):
        username = self.cleaned_data.get('username')
        password = self.cleaned_data.get('password')

        if username and password:
            self.user_cache = authenticate(username=username,
                                           password=password)
            if self.user_cache is None:
                raise forms.ValidationError(self.__errmsg['incorrect'])
            elif not self.user_cache.is_active:
                raise forms.ValidationError(self.__errmsg['inactive'])
        self.check_for_test_cookie()
        return self.cleaned_data
