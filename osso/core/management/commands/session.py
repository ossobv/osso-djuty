# vim: set ts=8 sw=4 sts=4 et ai tw=79:
from pprint import pformat

from django.conf import settings
from django.contrib.auth import SESSION_KEY
from django.contrib.auth.models import AnonymousUser, User
from django.contrib.sessions.models import Session
from django.utils.importlib import import_module
from osso.core.management.base import BaseCommand, CommandError, docstring


class Command(BaseCommand):
    __doc__ = help = docstring("""
    Show session data for a user or key.
    """)
    args = 'show|remove [session_key_or_username]'

    def handle(self, *usernames_or_session_keys, **kwargs):
        verbose = int(kwargs.get('verbosity', '1'))

        if (not usernames_or_session_keys or
                usernames_or_session_keys[0] not in ('show', 'remove')):
            raise CommandError('Required argument "show" or "remove" missing.')

        command = usernames_or_session_keys[0]
        lookup_args = self.get_lookup_args(usernames_or_session_keys[1:])
        sessions = self.get_sessions(**lookup_args)

        if command == 'show':
            self.show(sessions)
        elif command == 'remove':
            if all(not i for i in lookup_args.values()):
                raise CommandError('Refusing to remove all sessions. '
                                   'Supply one or more lookup arguments.')
            self.remove(sessions, quiet=(not verbose))
        else:
            raise NotImplementedError('Programming error')

    def get_lookup_args(self, usernames_or_session_keys):
        session_keys = set()
        user_ids = set()
        user_ids_and_names = dict(
            (User.objects.filter(username__in=usernames_or_session_keys)
             .values_list('username', 'id')))
        for username_or_session_key in usernames_or_session_keys:
            if username_or_session_key in user_ids_and_names:
                user_ids.add(user_ids_and_names[username_or_session_key])
            else:
                session_keys.add(username_or_session_key)

        return {'user_ids': user_ids, 'session_keys': session_keys}

    def get_sessions(self, user_ids=None, session_keys=None):
        session_qs = Session.objects.order_by()
        if session_keys:
            session_qs = session_qs.filter(session_key__in=session_keys)

        sesskey = SESSION_KEY  # probably "_auth_user_id"
        matches = []
        for session in session_qs:
            sess_dict = session.get_decoded()
            if not user_ids or sess_dict.get(sesskey) in user_ids:
                matches.append({
                    'session': session,
                    'decoded': sess_dict,
                    'user_id': sess_dict.get(sesskey, None),
                })

        return matches

    def show(self, sessions):
        user_map = dict((user.id, user) for user in (
            User.objects.filter(id__in=[i['user_id'] for i in sessions
                                        if i['user_id'] is not None])))
        user_map[None] = AnonymousUser()

        sessions.sort(key=(
            lambda x: (user_map[x['user_id']].username,
                       x['session'].expire_date)))

        last_user = None
        for data in sessions:
            session = data['session']
            decoded = data['decoded']
            user = user_map[data['user_id']]

            if user != last_user:
                if last_user is not None:
                    print  # tailing LF after each record
                print '%s:' % (user.username or '(anonymoususer)',)
                last_user = user
            print ' ', session.session_key, session.expire_date
            if decoded:
                decoded_printable = pformat(decoded)
                print '   ', '\n    '.join(decoded_printable.split('\n'))

        if sessions:
            print  # tailing LF

    def remove(self, sessions, quiet=False):
        engine = import_module(settings.SESSION_ENGINE)

        for data in sessions:
            if not quiet:
                print 'Deleting session', data['session'].session_key

            store = engine.SessionStore(data['session'].session_key)
            store.delete()
