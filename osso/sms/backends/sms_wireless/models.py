from django.db import models
from django.utils.translation import ugettext_lazy as _
from osso.core.models import SafeCharField

class DeliveryReportForward(models.Model):
    batch_prefix = SafeCharField(max_length=64, unique=True, help_text=_('The batch prefix to match delivery reports.'))
    destination = models.URLField(help_text=_('The URL to forward the delivery report to.'))

    def __unicode__(self):
        return '%s => %s' % (self.batch_prefix, self.destination)

class DeliveryReportForwardLog(models.Model):
    datetime = models.DateTimeField(auto_now_add=True, help_text=_('The datetime the response was forwarded.'))
    post_data = SafeCharField(max_length=512, help_text=_('The POST data.'))
    destination = SafeCharField(max_length=200, help_text=_('The destination the delivery report was forwarded to.'))
    batch_prefix = SafeCharField(max_length=64, help_text=_('The batch prefix that was matched.'))
    response = SafeCharField(max_length=512, blank=True, help_text=_('The response from the DLR destination.'))

    def __unicode__(self):
        return '%s: %s => %s' % (self.datetime, self.batch_prefix, self.destination)
