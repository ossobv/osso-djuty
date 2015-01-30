# vim: set ts=8 sw=4 sts=4 et ai:
try:  # Django 1.4+
    from django.conf.urls import patterns, url
except ImportError:  # Django 1.3-
    from django.conf.urls.defaults import patterns, url


urlpatterns = patterns('osso.userchat.views',
    url(r'^(?P<channel_id>\d+)/$', 'channel', name='userchat_channel'),
    url(r'^multiq/$', 'multiple_channels', name='userchat_multiple_channels'),
)
