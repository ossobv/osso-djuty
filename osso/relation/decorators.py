# vim: set ts=8 sw=4 sts=4 et ai:
from functools import update_wrapper

from django.contrib.auth import REDIRECT_FIELD_NAME
from django.core.exceptions import ObjectDoesNotExist
from django.http import HttpResponseRedirect
from django.utils.http import urlquote


class _CheckAuthenticatableContactLogin(object):
    '''
    Copied from the _CheckLogin from django.contrib.auth.decorators and
    customized to fit exactly one need.
    '''
    def __init__(self, view_func, login_url=None, redirect_field_name=REDIRECT_FIELD_NAME):
        if not login_url:
            from django.conf import settings
            login_url = settings.LOGIN_URL
        self.view_func = view_func
        self.login_url = login_url
        self.redirect_field_name = redirect_field_name

        # We can't blindly apply update_wrapper because it updates __dict__ and
        # if the view function is already a _CheckLogin object then
        # self.test_func and friends will get stomped. However, we also can't
        # *not* update the wrapper's dict because then view function attributes
        # don't get updated into the wrapper. So we need to split the
        # difference: don't let update_wrapper update __dict__, but then update
        # the (parts of) __dict__ that we care about ourselves.
        update_wrapper(self, view_func, updated=())
        for k in view_func.__dict__:
            if k not in self.__dict__:
                self.__dict__[k] = view_func.__dict__[k]

    def __get__(self, obj, cls=None):
        view_func = self.view_func.__get__(obj, cls)
        return _CheckAuthenticatableContactLogin(view_func, self.login_url, self.redirect_field_name)

    def __call__(self, request, *args, **kwargs):
        if not request.user.is_authenticated():
            path = urlquote(request.get_full_path())
            tup = self.login_url, self.redirect_field_name, path
            return HttpResponseRedirect('%s?%s=%s' % tup)

        if hasattr(request, 'active_relation'):
            relation = request.active_relation
        else:
            try:
                contact = request.user.authenticatablecontact
            except ObjectDoesNotExist:
                relation = None
            else:
                relation = contact.relation

        assert relation, 'User %s has no profile / no relation!' % (request.user,)
        return self.view_func(relation, request.user, request, *args, **kwargs)


def login_with_company_profile_required(func):
    '''
    Decorator for views that checks that the user is logged in and checks that
    the user has a valid profile and, which that checked, adds the company and
    user to the view function as first and second parameters, before the request
    object.
    '''
    return _CheckAuthenticatableContactLogin(func)
