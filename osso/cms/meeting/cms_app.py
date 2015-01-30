from cms.app_base import CMSApp
from cms.apphook_pool import apphook_pool
from django.utils.translation import ugettext_lazy as _

class MeetingApp(CMSApp):
    name = _('Meeting')
    urls = ['osso.cms.meeting.urls']

apphook_pool.register(MeetingApp)
