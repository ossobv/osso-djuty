# vim: set ts=8 sw=4 sts=4 et ai:
from datetime import datetime, timedelta

from django.contrib.auth.models import User
from django.core.cache import cache
from osso.aboutconfig.utils import aboutconfig
from osso.useractivity.models import UserActivityLog
from osso.useractivity.signals import logged_in, logged_out


CACHE_KEY_FMT = 'useractivity.user%d.ip%s'
IDLE_MAX_DEFAULT = 120
KEEP_DAYS_DEFAULT = 120


def mark_active(user_pk, ip_address, request=None):
    '''
    Mark already existing useractivitylog entries as not being expired
    (update the last_activity timestamp).

    If no entry is found, a new one is created as an "implicit login"
    and a logged_in signal is sent.

    The request object is passed so signal listeners can do something with it
    if needed.
    '''
    # Previously, we did this:
    #     updated = (UserActivityLog.objects
    #                .filter(user__pk=user_pk, explicit_logout=None)
    #                .update(last_activity=datetime.now()))
    #     if updated == 0: mark_login(...)
    #
    # However, that turned out to be very deadlock prone in postgres. A
    # second thread would do the same, and then this first transaction
    # would fail -- first at the end -- because the other one committed
    # it:
    #
    # (It looks like both threads get the SHARE LOCK and then
    # try to get the EXCLUSIVE LOCK.)
    # > 2010-08-26 11:30:45 CEST DETAIL:  Process 18487 waits for ShareLock on
    #     transaction 15611944; blocked by process 18488.
    # > Process 18488 waits for ShareLock on transaction 15611943; blocked by
    #     process 18487.
    # > Process 18487:
    #   UPDATE "useractivity_useractivitylog" SET "last_activity" =
    #     E'2010-08-26 11:30:44.699673'
    #   WHERE ("useractivity_useractivitylog"."user_id" = 2 AND
    #     "useractivity_useractivitylog"."explicit_logout" IS NULL)
    # > Process 18488:
    #   UPDATE "useractivity_useractivitylog" SET "last_activity" =
    #     E'2010-08-26 11:30:44.731305'
    #   WHERE ("useractivity_useractivitylog"."user_id" = 2 AND
    #     "useractivity_useractivitylog"."explicit_logout" IS NULL)
    # > 2010-08-26 11:30:45 CEST HINT:  See server log for query details.
    # > 2010-08-26 11:30:45 CEST STATEMENT:
    #   UPDATE "useractivity_useractivitylog" SET "last_activity" =
    #     E'2010-08-26 11:30:44.699673'
    #   WHERE ("useractivity_useractivitylog"."user_id" = 2 AND
    #     "useractivity_useractivitylog"."explicit_logout" IS NULL)
    #
    # So, instead, we separate the UPDATE from the SELECT and only
    # the timestamp if it is older than a certain amount of time.
    #
    # But first, we check the cache to see if we're not overdoing it.
    cache_key = CACHE_KEY_FMT % (user_pk, ip_address)

    log_ids = cache.get(cache_key)
    if log_ids is None:
        log_ids = list(UserActivityLog.objects.filter(
            user__pk=user_pk,
            ip_address=ip_address,
            explicit_logout=None
        ).values_list('id', 'last_activity'))

    if not log_ids:
        # There were no results? Implicit login
        mark_login(user_pk, ip_address=ip_address,
                   explicit_login=False, request=request)
    else:
        update_ids = []
        now = datetime.now()
        idle_max = int(aboutconfig('useractivity.idle_max', IDLE_MAX_DEFAULT))
        need_refresh_after = idle_max / 2 - 10  # 120 seconds -> 50
        old = now - timedelta(seconds=need_refresh_after)
        for i, (log_id, time) in enumerate(log_ids):
            if time < old:
                update_ids.append(log_id)
                log_ids[i] = (log_id, now)  # overwrite cache with new value
        # Update the last_activity on these items
        if update_ids:
            rows = UserActivityLog.objects.filter(
                id__in=update_ids,
                explicit_logout=None
            ).update(last_activity=now)
            # Updating less than expected?
            if rows != len(update_ids):
                mark_login(user_pk, ip_address=ip_address,
                           explicit_login=False, request=request)
            else:
                cache.set(cache_key, log_ids, 900)


def mark_login(user_pk, ip_address, explicit_login=True, request=None):
    '''
    Create a new useractivitylog entry.

    We'll create one even if there already exists an open entry. And
    then we send the logged_in signal.

    The request object is passed so signal listeners can do something
    with it if needed.
    '''
    # It's quite possible that we get multiple open entries at the same
    # time.  That'll be the users fault for logging on from multiple
    # locations.
    now = datetime.now()
    log = UserActivityLog.objects.create(
        user_id=user_pk,
        ip_address=ip_address,
        first_activity=now,
        last_activity=now,
        explicit_login=explicit_login
    )
    # Update cache
    cache_key = CACHE_KEY_FMT % (user_pk, ip_address)
    cache.set(cache_key, [(log.id, now)], 900)
    # Signal the listeners
    user = User.objects.get(pk=user_pk)
    logged_in.send(sender=User, instance=user, explicit=explicit_login,
                   request=request)


def mark_logout(user_pk, ip_address, explicit_logout=True):
    '''
    Mark all useractivitylog entries for this user as being expired.

    Note that if there is no log entry for this user, for whatever
    reason, no logged_out signal is sent either.
    '''
    # We don't have a notion of who is logged on from where, so only
    # marking the newest (or oldest) entry as logged out, makes no
    # sense whatsoever. (If there is no object at all, there is nothing
    # better to do than ignoring it.)
    cache_key = CACHE_KEY_FMT % (user_pk, ip_address)
    log_ids = cache.get(cache_key)
    cache.delete(cache_key)

    rows = UserActivityLog.objects.filter(
        user__pk=user_pk,
        ip_address=ip_address,
        explicit_logout=None
    ).update(
        last_activity=datetime.now(),
        explicit_logout=explicit_logout
    )

    if rows or log_ids:
        # The number of rows updated is not 0: someone logged out and
        # we have records.
        user = User.objects.get(pk=user_pk)
        logged_out.send(sender=User, instance=user, explicit=explicit_logout)


def prune_idlers(idle_max):
    '''
    Find useractivitylog entries that are still "open" (not logged out
    yet) but have been inactive for at least idle_max (seconds) time.

    For every user we log out, one logged_out signal is sent (with
    explicit set to Fale).

    Returns a list of users that were pruned.
    '''
    # Because we send signals for every user, we have to loop over all users.
    then = datetime.now() - timedelta(seconds=idle_max)
    prunable_users = (UserActivityLog.objects
                      .filter(explicit_logout=None, last_activity__lt=then)
                      .values_list('user_id', flat=True))

    # Get all pks first, then we only have to do 1 query to get the users.
    pruned_user_pks = []
    for user_pk in prunable_users:
        # Do the same timestamp check for every user so we lessen the chance
        # for race conditions.
        if (UserActivityLog.objects.filter(user__pk=user_pk,
                                           explicit_logout=None,
                                           last_activity__lt=then)
                                   .update(explicit_logout=False)):
            pruned_user_pks.append(user_pk)

    # Fire the signals
    pruned_users = list(User.objects.filter(pk__in=pruned_user_pks))
    for user in pruned_users:
        logged_out.send(sender=User, instance=user, explicit=False)

    return pruned_users


def prune_table(keep_days):
    """
    Prune the useractivity table of records older than N days.

    You should run this every now and then. Perhaps through the cleanup
    command that you run every minute, and then only once per 100 runs
    or so.
    """
    long_ago = datetime.today() - timedelta(days=keep_days)
    UserActivityLog.objects.filter(last_activity__lt=long_ago).delete()
