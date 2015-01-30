# vim: set ts=8 sw=4 sts=4 et ai tw=79:
import sys

from django.contrib.auth.models import User
from django.db.models import Q
from osso.core.management.base import BaseCommand, docstring
from osso.core.sessutil import ueber_logout


class Command(BaseCommand):
    __doc__ = help = docstring("""
    Purge the session table for a specific user.

    Specify a list of usernames or the special name @@staff to select
    all staff users.

    TODO: accept @groupname for group members.
    """)

    def handle(self, *usernames, **kwargs):
        verbose = int(kwargs.get('verbosity', '1'))

        usernames = set(usernames)

        try:
            usernames.remove('@@staff')
        except KeyError:
            query = Q()
        else:
            query = Q(is_staff=True)
        query |= Q(username__in=usernames)

        # Find users by is_staff=True and/or usernames, ordered by username.
        if query:
            items = (User.objects.filter(query).values_list('id', 'username')
                     .order_by('username'))
        else:
            items = ()
        found_usernames = [i[1] for i in items]
        found_user_ids = [i[0] for i in items]

        # Show which we found.
        if verbose >= 2:
            for item in items:
                print('%-7s %s' % ('%d.' % (item[0],), item[1]))

        # Show which we didn't find.
        for username in usernames:
            if username not in found_usernames:
                sys.stderr.write("warning: user '%s' not found\n" %
                                 (username,))

        # Log them out.
        if verbose >= 1:
            print('Preparing to remove session data for %d users' %
                  (len(found_user_ids,)))
        deleted = ueber_logout(found_user_ids)
        if verbose >= 1:
            print('Removed %d session data items' % (deleted,))
