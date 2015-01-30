# vim: set ts=8 sw=4 sts=4 et ai:


class BaseIdeal(object):
    def __init__(self, testing=False):
        '''
        We expect the constructor to (a) need no arguments and (b)
        accept an optional argument testing that signifies that we're
        in test mode. Use django.conf settings for account_ids and
        such.
        '''
        raise NotImplementedError()

    def get_banks(self):
        '''
        Returns something like:
        [{'id': 31, 'name': 'ABN Amro'},
         {'id': 91, 'name': 'Friesland Bank'}]
        '''
        raise NotImplementedError()

    def get_payment_form(self, payment, bank_id):
        '''
        Will convert a payment + bank_id into a form that can be auto-
        submitted. (In some cases it could be 302'd directly, but an
        auto-submit works too.)
        '''
        raise NotImplementedError()
