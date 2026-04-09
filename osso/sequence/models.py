from django.db import models
from django.utils.translation import gettext_lazy as _


class Sequence(models.Model):
    name = models.CharField(_('name'), max_length=63, primary_key=True)
    start = models.IntegerField(_('start'))
    increment = models.IntegerField(_('increment'))
    value = models.IntegerField(_('value'), blank=True, null=True)

    def __init__(self):
        return self.name
