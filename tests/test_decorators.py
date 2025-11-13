# vim: set ts=8 sw=4 sts=4 et ai:
from contextlib import contextmanager
from syslog import LOG_WARNING
from unittest.mock import patch, DEFAULT

from django.contrib.auth.models import AnonymousUser, User
from django.contrib.auth.signals import user_login_failed
from django.core.exceptions import PermissionDenied
from django.http import HttpRequest
from django.test import TestCase

from osso.core.decorators import expect_get, expect_post, log_failed_login


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

    @contextmanager
    def patch_log_failed_login(self):
        try:
            with patch.multiple('syslog', openlog=DEFAULT,
                                syslog=DEFAULT) as syslog:
                user_login_failed.connect(log_failed_login)
                yield syslog
        finally:
            user_login_failed.disconnect(log_failed_login)

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

        with self.patch_log_failed_login() as syslog:
            # Login requests that are not succesful will cause the
            # event to be logged.
            req = self.get_request('POST')
            user_login_failed.send(request=req, sender=None)
            assert syslog['openlog'].called, 'syslog was not called'
            assert syslog['syslog'].called, 'syslog was not called'
            expected = (LOG_WARNING,
                        '[django] Failed login for user from /unset/ port'
                        ' /unset/ (Host: /unset/)')
            self.assertEqual(syslog['syslog'].call_args[0], expected)
