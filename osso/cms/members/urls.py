try:  # Django 1.4+
    from django.conf.urls import patterns, url
except ImportError:  # Django 1.3-
    from django.conf.urls.defaults import patterns, url

urlpatterns = patterns('osso.cms.members.views',
    url(r'^groups/$', 'group', name='groups'),
    url(r'^group/add/$', 'group_add', name='group_add'),
    url(r'^group/(?P<group_id>\d+)/$', 'group_edit', name='group_edit'),
    url(r'^group/(?P<group_id>\d+)/delete/$', 'group_delete', name='group_delete'),
    url(r'^group/(?P<group_id>\d+)/member/add/$', 'group_add_member', name='group_add_member'),
    url(r'^group/(?P<group_id>\d+)/member/(?P<member_id>\d+)/remove/$', 'group_remove_member', name='group_remove_member'),

    url(r'^$', 'members', name='members'),
    url(r'^add/$', 'member_add', name='member_add'),
    url(r'^(?P<member_id>\d+)/$', 'member_edit', name='member_edit'),
    url(r'^(?P<member_id>\d+)/delete/$', 'member_delete', name='member_delete'),
)
