# vim: set ts=8 sw=4 sts=4 et ai:
from django.contrib.auth.models import User
from django.db import models
from django.utils.translation import ugettext_lazy as _
from osso.core.loanwords import car
from osso.core.models import Model, ParentField, PhoneNumberField, SafeCharField


class RelationManager(models.Manager):
    def descendants_of(self, relation, include=False):
        '''
        Returns only descendants of supplied relation, including the
        supplied relation if include is True.
        '''
        if relation is None:
            return self.get_query_set()
        items = list(self.get_query_set().order_by('owner__id'))
        ids_to_return = include and [relation.id] or []
        added_last = [relation.id]
        while True:
            added_last = [i.id for i in filter(lambda i: i.owner_id in added_last, items)]
            if not added_last:
                break
            ids_to_return.extend(added_last)
        return self.get_query_set().filter(id__in=ids_to_return)


class Relation(Model):
    '''
    A relation model: this can be a customer company, a business
    partner, a private person and even yourself. The owner is an
    optional parent to allow for recursive relationships. The name is
    freeform. The code is an optional code you use to identify your
    relation by. The foreign code is an optional code the relation uses
    to identify you by.

    >>> from osso.relation.models import Relation, Country, City, Address, AddressType

    >>> osso, osso_is_new = Relation.objects.get_or_create(
    ...     owner=None, name=u'OSSO B.V.', code=u'', foreign_code=u'')
    >>> gntel, gntel_is_new = Relation.objects.get_or_create(
    ...     owner=osso, name=u'gnTel B.V.', code=u'006', foreign_code=u'040055')
    >>> nl = Country.objects.get(code='nl')
    >>> groningen, groningen_is_new = City.objects.get_or_create(
    ...     country=nl, name=u'Groningen')
    >>> mediacentrale, is_new = Address.objects.get_or_create(
    ...   relation=gntel,
    ...   number=294,
    ...   complement=u'A',
    ...   street=u'Helperpark',
    ...   city=groningen
    ... )
    >>> mediacentrale.address_type.add(*AddressType.objects.exclude(identifier='OTHER'))

    >>> gntel.postal_address.street
    u'Helperpark'
    >>> gntel.postal_address.number
    294

    Assert that nameless relations get their pk as name.

    >>> nameless = Relation.objects.create(owner=gntel, code=u'123')
    >>> nameless.name == u'relation%d' % nameless.id
    True
    >>> nameless.code
    u'123'

    Clean up after ourself.

    >>> nameless.delete()
    >>> if gntel_is_new: gntel.delete()
    >>> if osso_is_new: osso.delete()
    >>> if groningen_is_new: groningen.delete()
    '''
    owner = ParentField(_('owner'), related_name='owned_set',
            help_text=_('This allows for reseller-style relationships. '
                        'Set to NULL for the system owner.'))
    name = SafeCharField(_('name'), max_length=63,
            help_text=_('The relation name: a company name or a person '
                        'name in case of a private person.'))
    code = SafeCharField(_('code'), max_length=16, blank=True,
            help_text=_('A human readable short relation identifier; should be unique per owner.'))
    foreign_code = SafeCharField(_('foreign code'), max_length=16, blank=True,
            help_text=_('A human readable identifier that the relation uses to identify you by.'))

    objects = RelationManager()

    @property
    def billing_address(self):
        """Return the billing address for this relation."""
        return car(self.address_set.filter(address_type__identifier='BILLING')
                   .order_by('created'))

    @property
    def delivery_address(self):
        """Return the delivery address for this relation."""
        return car(self.address_set.filter(address_type__identifier='DELIVERY')
                   .order_by('created'))

    @property
    def postal_address(self):
        """Return the postal address for this relation."""
        return car(self.address_set.filter(address_type__identifier='POSTAL')
                   .order_by('created'))

    @property
    def visiting_address(self):
        """Return the visiting address for this relation."""
        return car(self.address_set.filter(address_type__identifier='VISITING')
                   .order_by('created'))

    def is_descendant_of(self, relation, include=False):
        ''' Whether this is a child or grandchild of relation. Currently
        does N queries for N levels of grandparents. Beware! '''
        parent = (self.owner, self)[include]
        while parent and parent != relation:
            parent = parent.owner
        return parent is not None

    def save(self, *args, **kwargs):
        """Save the model to the database."""
        ParentField.check(self, 'owner')
        super(Relation, self).save(*args, **kwargs)
        if self.name == '':
            self.name = 'relation%d' % self.id
            super(Relation, self).save(force_update=True)

    def __unicode__(self):
        if self.code == '':
            return self.name
        return u'%s - %s' % (self.code, self.name)

    class Meta:
        """Django metaclass information."""
        ordering = ('name',)
        permissions = (('view_relation', 'Can view relation'),)
        verbose_name = _('relation')
        verbose_name_plural = _('relations')


class Contact(Model):
    '''
    A contact (a person) tied to a Relation.
    '''
    # XXX: 'name' should really sync itself with the user.forename /
    # user.surname if it is an authenticatable contact (and.. should we
    # split this name into a fore-/surname?)
    relation = models.ForeignKey(Relation, verbose_name=_('relation'))
    name = SafeCharField(_('name'), max_length=63, help_text=_('The full name of the contact.'))
    email = models.EmailField(_('e-mail address'), blank=True)

    def __unicode__(self):
        return self.name

    class Meta:
        """Django metaclass information."""
        permissions = (('view_contact', 'Can view contact'),)
        verbose_name = _('contact')
        verbose_name_plural = _('contacts')


class AuthenticatableContact(Contact):
    '''
    Model to store the user profile of a contact who can log in. This
    model is referred to by the AUTH_PROFILE_MODULE in the settings.
    '''
    user = models.ForeignKey(User, verbose_name=_('user'), unique=True)

    def __unicode__(self):
        return u'%s (%s)' % (self.user, self.relation)

    class Meta:
        """Django metaclass information."""
        verbose_name = _('authenticatable contact')
        verbose_name_plural = _('authenticatable contacts')


class Country(Model):
    '''
    The country. These are filled in by a fixture. No need to touch them.
    '''
    code = SafeCharField(_('code'), max_length=2, primary_key=True,
            help_text=_('The ISO 3166 alpha2 code in lowercase.'))
    name = SafeCharField(_('name'), max_length=63,
            help_text=_('The country name.'))
    order = models.PositiveIntegerField(_('order'), default=0,
            help_text=_('A non-zero number orders the countries highest first in select boxes '
                        '(use this for commonly used countries).'))

    def __unicode__(self):
        return self.name

    class Meta:
        """Django metaclass information."""
        ordering = ('-order', 'name')
        verbose_name = _('country')
        verbose_name_plural = _('countries')


class City(Model):
    '''
    The city. You may need to add lots of these.
    '''
    country = models.ForeignKey(Country, verbose_name=_('country'),
            help_text=_('Select the country the city lies in.'))
    name = SafeCharField(_('name'), max_length=63,
            help_text=_('The city name.'))

    def __unicode__(self):
        return (_(u'%(city)s (%(countrycode)s)') %
                {'city': self.name, 'countrycode': self.country.code})

    class Meta:
        """Django metaclass information."""
        ordering = ('name',)
        verbose_name = _('city')
        verbose_name_plural = _('cities')


class AddressType(Model):
    '''
    The different types of addresses. You won't need to change these.
    The initial data fixture makes sure you get BILLING, DELIVERY,
    POSTAL, VISIT and OTHER.

    The Relation model uses these types to get the billing_address and
    so forth from the available addresses.
    '''
    identifier = SafeCharField(_('identifier'), max_length=16,
            help_text=_('An identifier for machine lookups: e.g. "BILLING".'))
    description = SafeCharField(_('description'), max_length=63,
            help_text=_('A descriptive name: e.g. "Postal address".'))

    def __repr__(self):
        return 'AddressType::%s' % self.identifier

    def __unicode__(self):
        return self.description

    class Meta:
        """Django metaclass information."""
        verbose_name = _('address type')
        verbose_name_plural = _('address types')


class Address(Model):
    '''
    Every relation can have zero or more addresses. Most often, the
    relation will have only one address, with the types BILLING,
    DELIVERY, POSTAL and VISIT set. Using the address_type many2many
    field, you don't need to keep four addresses in sync.
    '''
    relation = models.ForeignKey(Relation, verbose_name=_('relation'),
            help_text=_('The relation this address belongs to.'))
    address_type = models.ManyToManyField(AddressType, verbose_name=_('address type'),
            help_text=_('Select one or more types of addresses.'))

    number = models.PositiveIntegerField(_('number'),
            help_text=_('The house number must be an integer, see the next field for extensions.'))
    complement = SafeCharField(_('complement'), max_length=32, blank=True,
            help_text=_('Optional house number suffixes.'))
    street = SafeCharField(_('street'), max_length=127,
            help_text=_('The street name, without number.'))
    city = models.ForeignKey(City, verbose_name=_('city'),
            help_text=_('The city.'))
    zipcode = SafeCharField(_('zip code'), max_length=16,
            help_text=_('Zip/postal code.'))

    contact = models.ForeignKey(Contact, blank=True, null=True,
            help_text=_('For the attention of'))

    def __unicode__(self):
        return _(u'%(relation)s addresses: %(address_types)s') % {
            'relation': self.relation,
            'address_types': ', '.join(unicode(addr) for addr in self.address_type.all()),
        }

    class Meta:
        """Django metaclass information."""
        ordering = ('relation__name',)
        permissions = (('view_address', 'Can view address'),)
        verbose_name = _('address')
        verbose_name_plural = _('addresses')


class PhoneNumber(Model):
    '''
    Phone usage and thereby assumptions based on phone numbers and phone
    number types are blurring. Therefore this PhoneNumber lacks a
    PhoneNumberType field. Instead, you get to pour your heart out in
    the freeform comment field. ("Work", "Home", "Mobile", "Only on
    sundays between 12:05 and 13:05" are all fine ;-) One special case
    could be "Fax" which you might want to pick automatically.)

    Because the comments and the activity-flag may differ, the phone
    numbers are not unique+m2m, but non-unique+one2one.
    '''
    relation = models.ForeignKey(Relation, verbose_name=_('relation'),
            related_name='phonenumber_set',
            help_text=_('The relation this phone number belongs to.'))
    number = PhoneNumberField(_('number'),
            help_text=_('The telephone number.'))
    active = models.BooleanField(_('active'), blank=True, default=True,
            help_text=_('Whether one should use this number.'))
    comment = SafeCharField(_('comment'), max_length=63, blank=True,
            help_text=_('Optional comments about the number\'s use (or "Fax").'))

    def __unicode__(self):
        return _(u'%(relation)s phone number: %(number)s%(comment)s%(active)s') % {
            'relation': self.relation,
            'number': self.number,
            'comment': (u'', u' (%s)' % self.comment)[self.comment != ''],
            'active': (_(' INACTIVE'), u'')[self.active],
        }

    class Meta:
        """Django metaclass information."""
        ordering = ('relation__name',)
        verbose_name = _('phone number')
        verbose_name_plural = _('phone numbers')
