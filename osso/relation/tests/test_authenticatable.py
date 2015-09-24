# vim: set ts=8 sw=4 sts=4 et ai:
from django.conf import settings
from django.contrib.auth.models import AnonymousUser, User
from django.contrib.sessions.middleware import SessionMiddleware
from django.http import HttpRequest
from django.test import TestCase

from osso.core.decorators import login_with_profile_required
from osso.relation.decorators import login_with_company_profile_required
from osso.relation.middleware import ActiveRelationMiddleware
from osso.relation.models import Relation, AuthenticatableContact
from osso.relation.utils import get_active_relation, set_active_relation


class AuthenticatableTestCase(TestCase):
    def setUp(self):
        self.contact_user = User.objects.create_user(username='contact',
                email='', password='contact2')
        self.relation = Relation.objects.create(name='Relation')
        AuthenticatableContact.objects.create(name='contact',
                relation=self.relation, user=self.contact_user)
        self.user = User.objects.create_user(username='user', email='',
                password='user2')

    def get_request(self, user):
        req = HttpRequest()
        # relation middleware depends on session middleware
        m = SessionMiddleware()
        m.process_request(req)
        req.user = user
        return req

    def test_middleware(self):
        middleware = ActiveRelationMiddleware()

        req = self.get_request(AnonymousUser())
        middleware.process_request(req)
        self.assertIsNone(req.active_relation)
        self.assertIsNone(req.active_relation_id)

        req = self.get_request(self.user)
        middleware.process_request(req)
        self.assertIsNone(req.active_relation)
        self.assertIsNone(req.active_relation_id)

        req = self.get_request(self.contact_user)
        middleware.process_request(req)
        self.assertEqual(req.active_relation, self.relation)
        self.assertEqual(req.active_relation_id, self.relation.pk)

    def test_profile_decorator(self):
        def test_view(request):
            return True

        req = self.get_request(AnonymousUser())
        response = login_with_profile_required(test_view)(req)
        self.assertTrue(response['Location'].startswith(settings.LOGIN_URL))

        req = self.get_request(self.user)
        with self.assertRaises(AssertionError):
            login_with_profile_required(test_view)(req)

        req = self.get_request(self.contact_user)
        self.assertTrue(login_with_profile_required(test_view)(req))

    def test_company_profile_decorator(self):
        def test_view(relation, user, request):
            return True

        req = self.get_request(AnonymousUser())
        response = login_with_company_profile_required(test_view)(req)
        self.assertTrue(response['Location'].startswith(settings.LOGIN_URL))

        req = self.get_request(self.user)
        with self.assertRaises(AssertionError):
            login_with_company_profile_required(test_view)(req)

        req = self.get_request(self.contact_user)
        self.assertTrue(login_with_company_profile_required(test_view)(req))

    def test_active_relation(self):
        relation = Relation.objects.create(name='Relation #2')
        req = self.get_request(AnonymousUser())
        self.assertIsNone(get_active_relation(req))
        set_active_relation(req, relation)
        # anonymous cannot take control of a relation
        self.assertIsNone(get_active_relation(req))

        req = self.get_request(self.user)
        self.assertIsNone(get_active_relation(req))
        set_active_relation(req, relation)
        # authenticated users can, even without a profile
        self.assertEqual(get_active_relation(req), relation)

        req = self.get_request(self.contact_user)
        # returns the users own relation
        self.assertEqual(get_active_relation(req), self.relation)
        set_active_relation(req, relation)
        # unless another relation is controlled
        self.assertEqual(get_active_relation(req), relation)
