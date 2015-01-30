# vim: set ts=8 sw=4 sts=4 et ai:
import re

class SequenceError(ValueError):
    pass

class SequenceDoesNotExist(SequenceError):
    pass

sequence_name_re = re.compile('^[a-zA-Z]{1}[a-zA-Z0-9_]{0,63}$')
class BaseSequence(object):
    '''
    Base Sequence class
    '''
    def create(self, name, start=1, increment=1):
        '''
        Create a sequence with identifier `name`
        '''
        raise NotImplementedError()

    def drop(self, name):
        '''
        Drop the sequence with identifier `name`
        '''
        raise NotImplementedError()

    def currval(self, name):
        '''
        return the current value of the sequence `name`
        '''
        raise NotImplementedError()

    def nextval(self, name):
        '''
        return the next value for the sequence `name`
        '''
        raise NotImplementedError()

    def setval(self, name, value):
        '''
        set the value for sequence `name` to `value`
        '''
        raise NotImplementedError()

    def install(self, **kwargs):
        '''
        hook to prepare the database for sequences
        '''
        pass

    def validate_name(self, name):
        '''
        validate if the given name is a valid sequence name
        '''
        match = sequence_name_re.match(name)
        if not match:
            raise SequenceError('invalid sequence name %r' % name)
