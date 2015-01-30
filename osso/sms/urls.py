# vim: set ts=8 sw=4 sts=4 et ai:
from django.conf import settings

try:  # Django 1.4+
    from django.conf.urls import patterns, url
except ImportError:  # Django 1.3-
    from django.conf.urls.defaults import patterns, url


if not hasattr(settings, 'SMS_BACKEND'):
    urlpatterns = patterns('osso.sms')
elif settings.SMS_BACKEND == 'osso.sms.backends.sms_console.ConsoleSmsBackend':
    urlpatterns = patterns('osso.sms.backends.sms_console.views',
        url(r'^in/$', 'incoming_text', name='sms_incoming_text'),
    )
elif settings.SMS_BACKEND == 'osso.sms.backends.sms_mollie.MollieSmsBackend':
    urlpatterns = patterns('osso.sms.backends.sms_mollie.views',
        url(r'^in/$', 'incoming_text', name='sms_incoming_text'),
        url(r'^dlr/$', 'delivery_report', name='sms_delivery_report'),
    )
elif settings.SMS_BACKEND == 'osso.sms.backends.sms_mollie2.MollieSmsBackend':
    urlpatterns = patterns('osso.sms.backends.sms_mollie2.views',
        url(r'^in/$', 'incoming_text', name='sms_incoming_text'),
        url(r'^dlr/$', 'delivery_report', name='sms_delivery_report'),
    )
elif settings.SMS_BACKEND == 'osso.sms.backends.sms_wireless.WirelessSmsBackend':
    urlpatterns = patterns('osso.sms.backends.sms_wireless.views',
        url(r'^in/$', 'incoming_text', name='sms_incoming_text'),
        url(r'^dlr/$', 'delivery_report', name='sms_delivery_report'),
    )
elif settings.SMS_BACKEND == 'osso.sms.backends.sms_zjipz.ZjipzSmsBackend':
    urlpatterns = patterns('osso.sms.backends.sms_zjipz.views',
        url(r'^in/$', 'incoming_text', name='sms_incoming_text'),
        url(r'^dlr/$', 'delivery_report', name='sms_delivery_report'),
    )
