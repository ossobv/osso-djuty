# vim: set ts=8 sw=4 sts=4 et ai:
"""
You'll probably want to instantiate the payment provider with code
similar to this::

    class PaymentBaseProceedView(CacheControlMixin, DetailView):
        '''
        Use the Cache mixin in an attempt to get fewer devices to re-attempt
        to view the redirect page (which breaks, because certain veriables
        are already set).
        '''
        cache_timeout = 365 * 86400  # a year..
        model = Payment

        def get_provider_instance(self):
            # Set provider_id on your subclass.
            return get_provider_by_id(self.provider_id).get_instance()

        def get_context_data(self, **kwargs):
            context = super(PaymentBaseProceedView, self).get_context_data(
                **kwargs)
            context.update({'form': self.get_form(self.get_object())})
            return context

        def get_form(self, payment):
            provider = self.get_provider_instance()
            form = provider.get_payment_form(payment)

            # The view will auto-submit the form through Javascript if
            # possible. We can therefore mark the Payment as submitted.
            payment.mark_submitted()

            return form

Some payment providers require additional parameters to the
get_payment_form: you can provide them in your subclass.
"""


class Provider(object):
    def __init__(self, testing=False):
        """
        We expect the constructor to (a) need no arguments and (b)
        accept an optional argument testing that signifies that we're
        in test mode. Use django.conf settings for account_ids and
        such.

        Note that this is not a hard requirement as we use the
        module-specific get_instance methods that may provide
        additional arguments.
        """
        raise NotImplementedError()

    def get_payment_form(self, payment):
        """
        Will convert a payment + bank_id into a form that can be auto-
        submitted. (In some cases it could be 302'd directly, but an
        auto-submit works too.)

        The signature of this function may certainly be extended beyond
        this. Use your "submit" views to tailor to the need and options
        of the provider.
        """
        raise NotImplementedError()


class IdealProvider(Provider):
    """
    An iDEAL payment provider may require you to choose the list of
    banks. If you implement an iDEAL provider that does not require you
    to select the banks, you can inherit from the regular Provider
    instead.
    """
    def get_banks(self):
        """
        Returns something like:
        [{'id': 31, 'name': 'ABN Amro'},
         {'id': 91, 'name': 'Friesland Bank'}]
        """
        raise NotImplementedError()

    def get_payment_form(self, payment, bank_id):
        """
        Will convert a payment + bank_id into a form that can be auto-
        submitted. (In some cases it could be 302'd directly, but an
        auto-submit works too.)
        """
        raise NotImplementedError()
