# vim: set ts=8 sw=4 sts=4 et ai:
from django.contrib import admin
from osso.relation.models import (Address, AuthenticatableContact, City,
    Contact, Country, PhoneNumber, Relation)


class AuthenticatableContactAdmin(admin.ModelAdmin):
    list_display = ('id', 'name', 'user', 'relation')


class RelationAdmin(admin.ModelAdmin):
    raw_id_fields = ('owner',)


admin.site.register(Address)
admin.site.register(AuthenticatableContact, AuthenticatableContactAdmin)
admin.site.register(City)
admin.site.register(Contact)
admin.site.register(Country)
admin.site.register(PhoneNumber)
admin.site.register(Relation, RelationAdmin)
