# vim: set ts=8 sw=4 sts=4 et ai tw=79:
from importlib import import_module

from django.conf import settings
from django.contrib.auth import SESSION_KEY
from django.contrib.auth.models import User
from django.contrib.sessions.models import Session


def ueber_logout(arg):
    """
    Flush logged in sessions for user so the user cannot log in with any
    old session anymore.

    Use this to log off a user when changing passwords or deactivating
    the user. Or use it to log off all is_staff users periodically.

    Takes a User or container of user_id's.

    Note that this only works for the regular django.contrib.auth app
    where SESSION_KEY holds the User.pk.
    """
    if isinstance(arg, User):
        user_ids = (arg.id,)
    elif hasattr(arg, '__contains__'):
        user_ids = arg
    else:
        raise TypeError("expected a User object or a container of user.id's, "
                        "got %r" % (arg,))

    engine = import_module(settings.SESSION_ENGINE)
    sesskey = SESSION_KEY  # probably "_auth_user_id"
    deleted = 0

    for session in Session.objects.order_by():
        sess_dict = session.get_decoded()
        if sess_dict.get(sesskey) in user_ids:
            # Going through the session store should make sure this
            # works immediately for cached backends as well.
            store = engine.SessionStore(session.session_key)
            store.delete()
            deleted += 1

    return deleted
