# vim: set ts=8 sw=4 sts=4 et ai:
from mock import patch, DEFAULT
from syslog import LOG_WARNING

from django.contrib.auth.models import AnonymousUser, User
from django.core.exceptions import PermissionDenied
from django.http import HttpRequest
from django.test import TestCase

from osso.core.decorators import expect_get, expect_post, log_failed_logins


class DecoratorTestCase(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username='user', email='',
            password='user2')

    def get_request(self, method, user=None):
        req = HttpRequest()
        req.method = method
        req.user = user or AnonymousUser()
        req.POST = {'username': self.user.username}
        return req

    def test_decorators(self):
        def test_view(request):
            return True

        req = self.get_request('GET')
        self.assertTrue(expect_get(test_view)(req))
        with self.assertRaises(PermissionDenied):
            req = self.get_request('POST')
            expect_get(test_view)(req)

        req = self.get_request('POST')
        self.assertTrue(expect_post(test_view)(req))
        with self.assertRaises(PermissionDenied):
            req = self.get_request('GET')
            expect_post(test_view)(req)

        req = self.get_request('GET')
        # log_failed_logins does not act on GET requests
        self.assertTrue(log_failed_logins(test_view)(req))
        with patch.multiple('syslog', openlog=DEFAULT,
                            syslog=DEFAULT) as syslog:
            # Login requests that are not succesful will cause the
            # event to be logged.
            req = self.get_request('POST')
            log_failed_logins(test_view)(req)
            assert syslog['openlog'].called, 'syslog was not called'
            assert syslog['syslog'].called, 'syslog was not called'
            expected = (LOG_WARNING,
                        b'[django] Failed login for user from /unset/ port '
                        b'/unset/ (Host: /unset/)')
            self.assertEqual(syslog['syslog'].call_args[0], expected)
        with patch.multiple('syslog', openlog=DEFAULT,
                            syslog=DEFAULT) as syslog:
            # Login requests that are will not be logged.
            req = self.get_request('POST', self.user)
            log_failed_logins(test_view)(req)
            assert not syslog['openlog'].called, 'syslog was called'
            assert not syslog['syslog'].called, 'syslog was called'
