# vim: set ts=8 sw=4 sts=4 et ai:
try:
    from django.contrib.contenttypes.fields import GenericForeignKey
except ImportError:
    from django.contrib.contenttypes.generic import GenericForeignKey
from django.contrib.contenttypes.models import ContentType
from django.db import models
from osso.search.manager import SearchManager


class Keyword(models.Model):
    keyword = models.SlugField(unique=True)

    def __unicode__(self):
        return self.keyword


class KeywordOccurrence(models.Model):
    keyword = models.ForeignKey(Keyword)
    frequency = models.PositiveIntegerField()
    weight = models.PositiveIntegerField()

    content_type = models.ForeignKey(ContentType)
    object_id = models.PositiveIntegerField()
    content_object = GenericForeignKey()

    objects = SearchManager()

    def __unicode__(self):
        return (u'%s, frequency=%d, weight=%d' %
                (self.keyword, self.frequency, self.weight))
