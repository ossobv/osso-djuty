# vim: set ts=8 sw=4 sts=4 et ai:
from django.conf import settings
try:
    from django.utils.deprecation import MiddlewareMixin
except ImportError:
    MiddlewareMixin = object

from osso.aboutconfig.utils import aboutconfig
from osso.useractivity import (IDLE_MAX_DEFAULT, mark_active, mark_login,
                               mark_logout, prune_idlers)


class UserActivityMiddleware(MiddlewareMixin):
    '''
    This middleware has to be loaded after the AuthenticationMiddleware, so it
    has access to the request.user property.

    This one is not so lazy as it checks the user object for every request.
    '''
    def process_request(self, request):
        # For speed reasons, we'll bypass the regular request.user.*
        # lookups and get the user_id from session directly. If we use
        # memcached users, this can save us a query or more.
        auth_userid = request.session.get('_auth_user_id')

        # Store the user_id to compare it after the request has been processed
        try:
            request._useractivitylog_user_pk = auth_userid
        except AttributeError:
            request._useractivitylog_user_pk = None  # AnonymousUser has no pk

        # A cronjob "./manage useractivity cleanup -v0" should be run every
        # minute or so.  It cleans up the activitylog, ridding it of open
        # entries of which the last_activity is too old.  This has to happen
        # or there will never be an "implicit logout".
        if settings.DEBUG:
            # .. or you could use this, sufficient for debug mode.
            prune_idlers(int(aboutconfig('useractivity.idle_max',
                                         IDLE_MAX_DEFAULT)))

        # Mark users as "active again" before the response is generated.  This
        # way the users logged_in signal can prepare new data for before the
        # view is loaded (that is, if it triggers an implicit login).
        if request._useractivitylog_user_pk is not None:
            user_pk = request._useractivitylog_user_pk
            ip_address = request.META['REMOTE_ADDR']
            mark_active(user_pk, ip_address=ip_address, request=request)

    def process_response(self, request, response):
        # If (due to some exceptional situation) the process_request is not
        # called we have no business here.
        if not hasattr(request, '_useractivitylog_user_pk'):
            return response

        # Hacks that save us a query, see above.
        auth_userid = request.session.get('_auth_user_id')

        # Compare the old user with the new one
        old_pk = request._useractivitylog_user_pk
        new_pk = auth_userid

        # Explicit login or explicit logout
        if new_pk != old_pk:
            ip_address = request.META['REMOTE_ADDR']
            if old_pk is not None:
                mark_logout(old_pk, ip_address=ip_address)
            if new_pk is not None:
                mark_login(new_pk, ip_address=ip_address, request=request)

        return response
