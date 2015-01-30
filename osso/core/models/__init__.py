# vim: set ts=8 sw=4 sts=4 et ai:
from django.conf import settings
from django.db import models
from osso.core.models.fields import *  # convenience


class Model(models.Model):
    '''
    Abstract Django Model that adds default created/modified fields and
    a clone method.
    '''
    created = models.DateTimeField(auto_now_add=True)
    modified = models.DateTimeField(auto_now=True)

    class Meta:
        ''' Django metaclass information. '''
        abstract = True


class ClonableMixin(object):
    def clone(self, **override_kwargs):
        '''
        Return an identical copy of the instance with a new id.
        Based on djangosnippets 1271 and 904 and extended to allow
        altered attributes (override_kwargs).
        '''
        if not self.pk:
            raise ValueError('Instance must be saved before it can be cloned.')
        opts = self._meta
        copy_kwargs = dict((i.name, getattr(self, i.name))
                           for i in opts.fields if i != opts.pk)
        copy_kwargs.update(override_kwargs)
        copy = self.__class__.objects.create(**copy_kwargs)
        # Add many2many relations
        for field in opts.many_to_many:
            source = getattr(self, field.attname)
            destination = getattr(copy, field.attname)
            destination.add(*source.all())
        return copy


# If osso.search is loaded, add delete and save methods that add
# indexing capabilities.
if 'osso.search' in settings.INSTALLED_APPS:
    from osso.search.utils import index_object, unindex_object

    class SearchableMixin(object):
        def save(self, force_insert=False, force_update=False, **kwargs):
            super(SearchableMixin, self).save(force_insert=force_insert,
                                              force_update=force_update,
                                              **kwargs)
            # save the object first so the object id is set
            # then let the search app index it
            index_object(self)

        def delete(self):
            # remove all references to the object from the search app
            unindex_object(self)
            super(SearchableMixin, self).delete()
