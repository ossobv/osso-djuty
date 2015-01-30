from django.contrib import admin

from osso.cms.meeting.models import Meeting, Invite, EmailMessage, EmailStyling

def date_time(obj):
    return u'%s %s' % (obj.date, obj.time)
date_time.short_description = 'Date time'

class MeetingAdmin(admin.ModelAdmin):
    list_display = (date_time, 'name',  'user', 'email_address' )
    ordering = ('-date', '-time',)
    fieldsets = (
        ('Meeting', {
            'fields': ('date', 'time', ('email_address', 'user'), 'name', 'pin_code', 'subject', 'group')
        }),
    )

class InviteAdmin(admin.ModelAdmin):
    list_display = ('created', 'member', 'meeting', 'accept')
    ordering = ('-created', 'meeting')

class EmailMessageAdmin(admin.ModelAdmin):
    list_display = ('email_address', 'subject', 'created', 'delivered')
    ordering = ('-created',)

admin.site.register(Meeting, MeetingAdmin)
admin.site.register(Invite, InviteAdmin)
admin.site.register(EmailMessage, EmailMessageAdmin)
admin.site.register(EmailStyling)
