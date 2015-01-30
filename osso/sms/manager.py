# vim: set ts=8 sw=4 sts=4 et ai:
from django.db import models
from osso.core import pickle


class OperatorManager(models.Manager):
    '''
    Updates the create, get and get_or_create methods to take an
    entire_code argument.
    '''
    def _split_entire_code(self, kwargs):
        if 'entire_code' in kwargs:
            from osso.relation.models import Country
            from osso.sms.models import OperatorCountryCode
            assert 'code' not in kwargs and 'country' not in kwargs, 'Can\'t have both entire_code and parts of it.'
            entire_code = kwargs.pop('entire_code')
            code = ''.join([i for i in entire_code if i in '0123456789'])
            # Actually.. we only expect 5, but Mollie sometimes sends
            # 238017 (dk? 3 digits?) for Dutch phone numbers.. which is
            # crap obviously. Example number: 31636569618
            assert len(code) in (5, 6), 'Expected operator code to contain exactly 5 or 6 digits.'

            try:
                country = OperatorCountryCode.objects.get(code=int(code[0:3])).country
            except OperatorCountryCode.DoesNotExist:
                assert False, 'Operator country not found!'

            kwargs['country'] = country
            kwargs['code'] = int(code[3:])

        return kwargs

    def create(self, *args, **kwargs):
        return super(OperatorManager, self).create(*args, **self._split_entire_code(kwargs))

    def get(self, *args, **kwargs):
        return super(OperatorManager, self).get(*args, **self._split_entire_code(kwargs))

    def get_or_create(self, *args, **kwargs):
        return super(OperatorManager, self).get_or_create(*args, **self._split_entire_code(kwargs))


class TextMessageManager(models.Manager):
    '''
    Updates the create method to take a meta argument which can take
    any serializable object (instead of the metadata argument which
    is a serialized string).
    '''
    def create(self, *args, **kwargs):
        if 'meta' in kwargs:
            from osso.sms.models import TextMessage
            assert 'metadata' not in kwargs, 'Can\'t have both meta and metadata.'
            meta = kwargs.pop('meta')
            if meta not in (None, ''):
                kwargs['metadata'] = pickle.dumpascii(meta)

        return super(TextMessageManager, self).create(*args, **kwargs)
