# vim: set ts=8 sw=4 sts=4 et ai:
try:  # Django 1.4+
    from django.conf.urls import patterns, url
except ImportError:  # Django 1.3-
    from django.conf.urls.defaults import patterns, url


urlpatterns = patterns('osso.sms.backends.sms_wireless.views',
    url(r'^dlrfw/$', 'delivery_report_forward'),
)
