# vim: set ts=8 sw=4 sts=4 et ai:
import decimal
import random
from datetime import datetime
from django.conf import settings
from django.contrib.auth.models import User
from django.db import connection, models
from django.utils.translation import ugettext_lazy as _


# TODO: update the mark_* values in open instance?


class Payment(models.Model):
    '''
    Holds state of payment transactions.
    '''
    created = models.DateTimeField(
        _('created'), auto_now_add=True,
        help_text=_('When this object was created.'))

    realm = models.CharField(
        _('realm'), max_length=31, blank=True,
        help_text=_('Realm/domain/host where this payment is done '
                    '(e.g. yoursite1.com); include scheme:// so we '
                    'know where to return your request.'))
    paying_user = models.ForeignKey(
        User, verbose_name=_('paying user'), blank=True, null=True,
        help_text=_('The user which is making the payment, if applicable.'))

    description = models.CharField(
        _('description'), max_length=255,
        help_text=_('A description of the payment. Keep it short.'))
    amount = models.DecimalField(
        _('amount'), max_digits=9, decimal_places=2,
        help_text=_('The amount of money being transferred.'))
    currency = models.CharField(
        _('currency'), max_length=3, blank=True,
        help_text=_('The currency of the transaction (e.g. EUR/USD) or '
                    'empty if currency-agnostic.'))

    transfer_initiated = models.DateTimeField(
        _('transfer initiated'), blank=True, null=True,
        # just before posting data to the bank
        help_text=_('When the request to the bank was made.'))
    transfer_allowed = models.DateTimeField(
        _('transfer allowed'), blank=True, null=True,
        # when a valid response from the bank was received
        help_text=_('When the bank responsed positively.'))
    transfer_finalized = models.DateTimeField(
        _('transfer finalized'), blank=True, null=True,
        # final response from the bank
        help_text=_('When the bank confirmed/reject the transaction.'))
    transfer_revoked = models.DateTimeField(
        _('transfer revoked'), blank=True, null=True,
        # not used too often, I hope
        help_text=_('If the bank revoked the transaction after '
                    'finalizing it.'))

    # Note here that a failed transaction is_success=False and
    # transfer_revoked=None and a revoked (previously succesful)
    # transaction has is_success=False and transfer_revoked=(set).
    # THIS IS NOT EDITABLE THROUGH THE ADMIN! WE DON'T WANT ADMINS TO
    # MESS WITH THIS!
    is_success = models.NullBooleanField(
        _('is success'), blank=True, null=True, editable=False, db_index=True,
        help_text=_('Is None until transfer_finalized is set at which '
                    'point it is True for success and False for failure. '
                    'If for some reason the transaction is revoked after '
                    'success, it can flip from True to False.'))

    unique_key = models.CharField(
        _('unique key'), max_length=64, blank=True, db_index=True,
        help_text=_('Max. 64 bytes of unique key, e.g. randbits||-||pk. '
                    'Will be unique if set.'))
    blob = models.TextField(
        _('blob'), blank=True,
        help_text=_('Can hold free form data about the transaction. '
                    'Use it to store transaction and/or debug info from '
                    'the bank.'))

    def atomic_update(self, filter_kwargs, update_kwargs):
        '''
        Perform an update of a column and return whether it succeded so
        we can return an error if the update was not supposed to happen.

        Note that some databases (MongoDB!) do not return whether an
        update changed any rows; it probably is not relevant for NoSQL
        (non-ACID) storage either. In that case we will update and
        always return true.
        '''
        # non-ACID db?
        is_BASE = bool('mongodb' in connection.settings_dict['ENGINE'])

        count = Payment.objects.filter(id=self.id, **filter_kwargs).update(
            **update_kwargs)
        if is_BASE or count == 1:
            for key, value in update_kwargs.items():
                setattr(self, key, value)
            return True

        # If you want the values update to the from-database ones,
        # you'll have to do it yourself.
        return False

    @property
    def state(self):
        if self.transfer_revoked:
            return 'revoked'
        if self.transfer_finalized:
            return 'final'
        if self.transfer_allowed:
            return 'processing'
        if self.transfer_initiated:
            return 'submitted'
        return 'unsent'

    @property
    def status(self):
        '''The status of the payment as used for provider.get_url(status)'''
        if self.is_success is None:
            return 'toosoon'
        elif self.is_success:
            return 'success'
        else:
            return 'abort'

    def get_amount(self):
        '''
        Some databases (MongoDB!) don't have a 'decimal' type and store
        the decimal as a string. Use this function to be sure you get a
        decimal type.
        '''
        return decimal.Decimal(self.amount)

    def get_url(self, when):
        '''
        URL to jump to on success/abort/ou-need-to-wait-some-more.
        '''
        # Create: success_url, abort_url, toosoon_url
        path = settings.OSSO_PAYMENT.get('%s_url' % (when,), '/')
        try:
            path = path % (self.id,)
        except TypeError:
            pass

        scheme_and_host = self.realm
        if '://' not in scheme_and_host:
            scheme_and_host = 'http://%s' % (scheme_and_host,)

        return '%s%s' % (scheme_and_host, path)

    def get_unique_key(self):
        '''
        Returns an ASCII string between 32 and 64 octets long.
        If you need something unique, this will do. If you want to store
        a foreign transaction_id here, use set_unique_key() first.
        '''
        if not self.pk:
            raise ValueError('Cannot create unique key for object without pk')
        if self.unique_key:
            return self.unique_key

        unique_key = '%x-%s' % (
            random.getrandbits(128), self.id)  # 32 bytes + n bytes
        if not self.atomic_update({'unique_key': ''},
                                  {'unique_key': unique_key}):
            self.unique_key = Payment.objects.get(id=self.id).unique_key

        return str(self.unique_key)

    def set_unique_key(self, unique_key):
        '''
        If you want full control over the unique key or if you want to
        store a transaction identifier here, use this. Now it's your job
        to ensure uniqueness if you (ever) need it. (Preferably by
        appending "-<PK>" to the key for consistency with automatic
        unique key generation.)
        '''
        if self.unique_key:
            raise ValueError('Cannot reset an already set unique key')

        if not self.atomic_update(
                {'unique_key': ''},
                {'unique_key': unique_key}):
            raise ValueError(
                'Failed to set unique_key because it was already set in DB')

    def mark_submitted(self):
        '''Atomic setting of initiated time.'''
        if not self.atomic_update(
                {'transfer_initiated': None, 'is_success': None},
                {'transfer_initiated': datetime.now()}):
            raise ValueError(
                'Attempt to mark Payment %s as initiated, failed' % (self.id,))

    def mark_passed(self):
        '''
        Atomic setting of allowed time.

        Observe that this state is generally set just before mark_succeded.
        Passed should mean that the payment *is* complete and that the
        transaction can continue. Don't abuse it as meaning "submitted".

        See also: the payment_updated 'passed' vs. 'aborted' signals.
        '''
        if not self.atomic_update(
                {'transfer_allowed': None, 'is_success': None},
                {'transfer_allowed': datetime.now()}):
            raise ValueError(
                'Attempt to mark Payment %s as allowed, failed' % (self.id,))

    def mark_succeeded(self):
        '''Atomic setting of finalized time + success.'''
        if not self.atomic_update(
                {'transfer_finalized': None, 'is_success': None},
                {'transfer_finalized': datetime.now(), 'is_success': True}):
            raise ValueError(
                'Attempt to mark Payment %s as succeeded, failed' % (self.id,))

    def mark_aborted(self):
        '''Atomic setting of finalized time + failure.'''
        if not self.atomic_update(
                {'transfer_allowed': None, 'transfer_finalized': None,
                 'is_success': None},
                {'transfer_finalized': datetime.now(), 'is_success': False}):
            raise ValueError(
                'Attempt to mark Payment %s as finalized+failed, failed' %
                (self.id,))

    def set_blob(self, blob, overwrite=False):
        if overwrite:
            Payment.objects.filter(id=self.id).update(blob=blob)
            self.blob = blob
        elif not self.atomic_update(
                {'blob': ''},
                {'blob': blob}):
            raise ValueError(
                'Attempt to set Payment %s empty blob to something, failed' %
                (self.id,))

    def __unicode__(self):
        return '%s (#%s %s %s %s)' % (
            self.description, self.id, self.paying_user or '(no one)',
            self.is_success and 'paid' or 'unpaid', self.get_amount())

    class Meta:
        verbose_name = _('payment')
        verbose_name_plural = _('payments')
