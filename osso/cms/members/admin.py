from django.contrib import admin

from osso.cms.members.models import Member, Group

class MemberAdmin(admin.ModelAdmin):
    list_display = ('name', 'email_address', 'phone_number')

admin.site.register(Member, MemberAdmin)
admin.site.register(Group)
