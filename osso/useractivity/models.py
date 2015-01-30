# vim: set ts=8 sw=4 sts=4 et ai:
from django.contrib.auth.models import User
from django.db import connection, models
from django.utils.translation import ugettext_lazy as _


class UserActivityLogManager(models.Manager):
    def __init__(self):
        super(UserActivityLogManager, self).__init__()

        # Init the subquery
        qn = connection.ops.quote_name
        self._where = '''
            %(table)s.%(id)s IN (
                SELECT MAX(%(id)s) AS %(id)s
                FROM %(table)s
                WHERE %(user_id)s IN (%%s)
                GROUP BY %(user_id)s
            )
        ''' % {
            'id': qn('id'),
            'table': qn('useractivity_useractivitylog'),
            'user_id': qn('user_id')
        }
        # Collapse spaces
        self._where = ' '.join(i for i in self._where.split() if i != '')

    def get_latest_for_user_pks(self, user_pks):
        if not len(user_pks):
            return UserActivityLog.objects.get_empty_query_set()
        # We assume we're dealing with integer pk's here.
        user_pk_list = ','.join(str(i) for i in user_pks)
        return (UserActivityLog.objects
                .extra(where=[self._where % user_pk_list])
                .select_related('user').order_by('user__username'))


class UserActivityLog(models.Model):
    '''
    Keep track of user activity (logging in and logging out).

    This is a basic model that doesn't care about location/session of logon.
    This means that when a user logs on with a different session (e.g. from a
    different IP or to a different hostname) events might not happen as you
    would expect. For instance, when a user logs out, all open activity
    records are closed.
    '''
    user = models.ForeignKey(User,
            help_text=_('The user we\'re tracking logins and logouts of.'))
    ip_address = models.IPAddressField(blank=False,
            help_text=_('The IP address of the user when logging in.'))
    first_activity = models.DateTimeField(blank=False,
            help_text=_('The time the user logged on.'))
    explicit_login = models.BooleanField(blank=True,
            help_text=_('Whether the login was implicit (reuse of a session) '
                        'or explicit (the login button).'))
    last_activity = models.DateTimeField(db_index=True,
            help_text=_('The time of the user\'s last activity (or logout '
                        'time, in case explicit_logout is set).'))
    explicit_logout = models.NullBooleanField(blank=True, null=True,
            default=None, db_index=True,
            help_text=_('Whether the logout was implicit (idle for too long) '
                        'or explicit (the logout button).'))

    objects = UserActivityLogManager()

    @property
    def duration(self):
        return self.last_activity - self.first_activity

    @property
    def is_online(self):
        return self.explicit_logout is None

    def __unicode__(self):
        kwargs = {
            'user': self.user.username,
            'implicit': (_(' implicitly'), u'')[self.explicit_login],
            'login_datetime': self.first_activity,
        }
        if self.explicit_logout is None:
            return (_('%(user)s logged in %(login_datetime)s%(implicit)s and '
                     'is active') % kwargs)
        else:
            kwargs.update({
                'logout_datetime': self.last_activity,
                'implicit2': (_(' implicitly'), u'')[self.explicit_logout],
            })
            return (_('%(user)s logged in %(login_datetime)s%(implicit)s '
                      'and logged out %(logout_datetime)s%(implicit2)s') %
                    kwargs)

    class Meta:
        permissions = (
            ('view_useractivitylog', 'Can view useractivitylog'),
        )
