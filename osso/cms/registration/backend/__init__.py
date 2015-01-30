# vim: set ts=8 sw=4 sts=4 et ai:
from registration.backends.default import DefaultBackend

from osso.cms.registration.forms import (
    NewsletterRegistrationForm as RegistrationForm)
from osso.cms.registration.models import NewsletterRegistration


class Backend(DefaultBackend):
    def register(self, request, **kwargs):
        new_user = super(Backend, self).register(request, **kwargs)
        if kwargs['name']:
            new_user.name = kwargs['name']
            new_user.save()

        if 'newsletter' in kwargs:
            NewsletterRegistration.objects.create(
                user=new_user,
                keep_informed=kwargs['newsletter'],
                active=False
            )
        return new_user

    def activate(self, request, activation_key):
        activated = super(Backend, self).activate(request, activation_key)
        print(activated)
        if activated:
            newsletter_reg = activated.newsletterregistration
            newsletter_reg.active = True
            newsletter_reg.save()
        return activated

    def get_form_class(self, request):
        """
        Return the default form class used for user registration.

        """
        return RegistrationForm
