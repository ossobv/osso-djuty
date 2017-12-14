# vim: set ts=8 sw=4 sts=4 et ai:
from datetime import datetime, timedelta

from django.contrib.auth.models import User, Group
from django.core.cache import cache
from django.core.urlresolvers import reverse
from django.db import models
from django.db.models.signals import post_save
from django.utils.translation import ugettext_lazy as _
from osso.core.models import Model, SafeCharField
from osso.relation.models import Relation
from osso.userchat import filters


CACHE_TIME = 300

# We touch filters here because we assume the models file to be called
# at once during startup. This should initialize the filters lists.
filters


class Channel(Model):
    '''
    A channel that holds a set of chat messages and binds them to a
    particular relation (company).
    '''
    relation = models.ForeignKey(Relation,
            help_text=_('The relation whose authenticated contacts can read/'
                        'write to this channel.'))
    name = SafeCharField(max_length=32,
            help_text=_('The name of the channel, e.g. "Operator chat".'))
    groups = models.ManyToManyField(Group,
            help_text=_('Users must be a member of one of these groups to '
                        'read/write to this channel.'))
    max_age = models.PositiveIntegerField(default=86400,
            help_text=_('The max age of the messages (in seconds) that are '
                        'kept for this channel. Set to 0 for eternity.'))
    max_count = models.PositiveIntegerField(default=2000,
            help_text=_('The max amount of messages that are kept for this '
                        'channel. Set to 0 for unlimited.'))

    def create_message(self, body, sender=None):
        return Message.objects.create(channel=self, sender=sender, body=body)

    def prune(self):
        '''
        Make sure the channel gets cleared of old messages.
        '''
        if self.max_age != 0:
            old = datetime.now() - timedelta(seconds=self.max_age)
            self.messages.filter(timestamp__lt=old).delete()
        if self.max_count != 0:
            count = self.messages.count()
            if count > self.max_count:
                # Don't delete all (count - max_count) for two reasons:
                # (1) If we're in a race condition, it's possible we'll
                #     delete way too many records.
                # (2) The queries might take too long.
                # (note, these two cases only happen when someone has
                # reduced the max_count value recently)
                limit = min(100, count - self.max_count)
                # Wrap the queryset in a list because of django-1.1 bug #12328
                # http://code.djangoproject.com/ticket/12328
                qs = Message.objects.order_by('timestamp')[0:limit]
                message_ids = list(qs.values_list('id', flat=True))
                Message.objects.filter(id__in=message_ids).delete()

    def get_absolute_url(self):
        return reverse('userchat_channel', kwargs={'channel_id': self.id})

    def __unicode__(self):
        return repr(self)

    def __repr__(self):
        return (u'Channel(name=%s, relation_id=%d)' %
                (repr(self.name), self.relation.id))

    class Meta:
        ordering = ('id',)
        unique_together = ('relation', 'name')


class Message(models.Model):
    '''
    A text message between users of the application.
    This could be an operator chat between authenticated users of a company.
    '''
    timestamp = models.DateTimeField(auto_now_add=True,
            help_text=_('The time the message was written.'))
    channel = models.ForeignKey(Channel, related_name='messages',
            help_text=_('The channel that the message belongs to.'))
    sender = models.ForeignKey(User, blank=True, null=True,
            related_name='userchat_messages',
            help_text=_('The user that wrote the message or NULL if it was a '
                        'system message.'))
    body = models.TextField(blank=False,
            help_text=_('The message body.'))

    def __unicode__(self):
        return repr(self)

    def __repr__(self):
        return (u'Message(timestamp=%s, channel_id=%s, sender=%s)' %
                (self.timestamp, self.channel.id, self.sender))


# Dirty the channel cache after a new message.
# And, prune messages after every new message.
# It would be even better if this was deferred until after the request
# is completed, so the response wasn't bothered by it. An alternative
# is to use a cronjob, but then we'd lose the older-history-as-long-as-
# no-one-writes-anything feature.
def _dirty_cache_and_prune_messages(instance=None, **kwargs):
    cache.set('osso.userchat.channel%d' % instance.channel.id, instance.id,
              CACHE_TIME)
    instance.channel.prune()
post_save.connect(_dirty_cache_and_prune_messages, sender=Message)
