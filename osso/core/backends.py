# vim: set ts=8 sw=4 sts=4 et ai:
from django.contrib.auth.backends import ModelBackend
from django.contrib.auth.models import User


__all__ = ('EmailBackend',)


class EmailBackend(ModelBackend):
    '''
    Custom authentication backend which uses the email address rather
    than the username to authenticate.
    '''
    def authenticate(self, email=None, password=None, username=None, **kwargs):
        try:
            # Match the user's email address to the entered 'username'.
            user = User.objects.get(email=username)
            if user.check_password(password):
                return user
            else:
                return None
        except User.DoesNotExist:
            return None
