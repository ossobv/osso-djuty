from django.contrib import admin

from osso.cms.registration.models import NewsletterRegistration

class NewsletterRegistrationAdmin(admin.ModelAdmin):
    list_display = ('__unicode__', 'keep_informed', 'active')

admin.site.register(NewsletterRegistration, NewsletterRegistrationAdmin)
