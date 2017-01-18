from django.db import models
from django.contrib.auth.models import User

class NewsletterRegistration(models.Model):
    user = models.OneToOneField(User)
    keep_informed = models.BooleanField(default=False)
    active = models.BooleanField(default=False)

    def __unicode__(self):
        return self.user.email
