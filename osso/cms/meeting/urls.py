try:  # Django 1.4+
    from django.conf.urls import include, patterns, url
except ImportError:  # Django 1.3-
    from django.conf.urls.defaults import include, patterns, url

urlpatterns = patterns('osso.cms.meeting.views',
    url(r'^$', 'invite', name='invite'),
    url(r'^meeting/$', 'meeting', name='meeting'),
    url(r'^meeting/(?P<meeting_id>\d+)/$', 'meeting_detail', name='meeting_detail'),
    url(r'^invite/(?P<invite_id>\d+)/accept/(?P<token>\w+)/$', 'meeting_invite_accept', name='meeting_invite_accept'),
    url(r'^invite/(?P<invite_id>\d+)/reject/(?P<token>\w+)/$', 'meeting_invite_reject', name='meeting_invite_reject'),
    url(r'^captcha/', include('captcha.urls')),
)
