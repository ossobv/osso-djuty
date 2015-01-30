# vim: set ts=8 sw=4 sts=4 et ai:
from django.core.cache import cache
from django.core.exceptions import PermissionDenied
from django.shortcuts import get_object_or_404
from osso.core.decorators import login_with_profile_required
from osso.userchat.filters import pre_send_run
from osso.userchat.models import CACHE_TIME, Channel, Message
from osso.xhr import JsonResponse


def messages_to_json(messages, user=None):
    '''
    Convert a list of channel messages to something usable, JSON-wise.
    '''
    json = []
    for msg in messages:
        value = {
            'id': msg.id,
            'time': msg.timestamp.strftime('%H:%M'),
            'body': msg.body,
        }
        if msg.sender is not None:
            value['sender'] = msg.sender.username

        extra_class = []
        if user == msg.sender:
            extra_class.append('is-my-message')
        if len(extra_class):
            value['extra_class'] = ' '.join(extra_class)
        json.append(value)
    return json


def qarg_to_pairs(string_q):
    '''
    Convert a string of dash-delimited integers to a list of 2-tuples.
    E.g. 1-0-2-0 to [(1, 0), (2, 0)].
    '''
    try:
        tmp = [int(i) for i in string_q.split('-')]
    except ValueError:
        return []
    if len(tmp) % 2 != 0:
        return []

    ret = []
    for i in range(0, len(tmp), 2):
        ret.append((tmp[i], tmp[i + 1]))
    return ret


@login_with_profile_required
def channel(request, channel_id):
    # The optional argument gt=<id>
    try:
        last_message_id = int(request.GET.get('gt', 0))
    except ValueError:
        last_message_id = 0

    # Get all necessary prerequisites
    group_ids = list(request.user.groups.values_list('id', flat=True))
    exclude_empty_sender = False
    try:
        relation_id = request.active_relation_id
    except AttributeError:
        relation_id = request.user.get_profile().relation_id
    channels = Channel.objects.filter(relation__id=relation_id,
                                      groups__in=group_ids).distinct()
    channel = get_object_or_404(channels, pk=channel_id)

    # Add message if this is a post request
    if request.method == 'POST':
        try:
            body = request.POST.get('body')
        except IOError:
            # As this is loaded through AJAX asynchronously, it can
            # happen that the client disconnects during the POST:
            # IOError: Client read error (Timeout?)
            return JsonResponse(request, '[]')

        if body is not None:
            body = body.strip()
            if body != '':
                channel.create_message(body=body, sender=request.user)

    # Get messages greater than last_message_id
    message_qs = channel.messages.filter(id__gt=last_message_id)
    if exclude_empty_sender:
        message_qs = message_qs.exclude(sender=None)
    messages = (message_qs.select_related('sender').order_by('timestamp')
                .distinct())

    # Run it through the message filters.
    final_messages = []
    for message in messages:
        message = pre_send_run(message, channel_id=channel_id,
                               group_ids=group_ids)
        if message:
            final_messages.append(message)

    json = messages_to_json(final_messages, user=request.user)
    return JsonResponse(request, json, compact=True)


# Don't require login with profile here yet. First check it later on
# when the cache tells us that there *are* new messages and we need to
# fetch them. This saves us a query. For the userchat /multiq/ that's
# pretty much, since a lot of users call this every couple of seconds.
def multiple_channels(request):
    # The argument q=<string> holds the channel_id-gt_value tuples, e.g.
    # 1-0-2-45 means channel 1 from id 0 and channel 2 from id 45.
    pairs = qarg_to_pairs(request.GET.get('q'))

    # Get all necessary prerequisites first when we need them
    json = {}
    relation_id, group_ids, exclude_empty_sender = None, None, False

    for channel_id, message_id in pairs:
        # The cache stores the last message id. If we're looking for a
        # different id, go do actual work.
        cache_key = 'osso.userchat.channel%d' % channel_id
        if cache.get(cache_key) != message_id:
            if relation_id is None:
                if request.user.is_anonymous():
                    raise PermissionDenied()
                try:
                    relation_id = request.active_relation_id
                except AttributeError:
                    try:
                        relation_id = request.user.get_profile().relation_id
                    except:
                        raise PermissionDenied()
                group_ids = list(request.user.groups
                                 .values_list('id', flat=True))

            message_qs = Message.objects.filter(
                id__gt=message_id,
                channel__id=channel_id,
                channel__relation__id=relation_id,
                channel__groups__in=group_ids
            )
            if exclude_empty_sender:
                message_qs = message_qs.exclude(sender=None)
            messages = list(message_qs.select_related('sender')
                            .order_by('timestamp').distinct())

            # Run it through the message filters.
            final_messages = []
            for message in messages:
                message = pre_send_run(message, channel_id=channel_id,
                                       group_ids=group_ids)
                if message:
                    final_messages.append(message)

            if len(final_messages):
                json[channel_id] = messages_to_json(final_messages,
                                                   user=request.user)
            if len(messages):
                # Store the last one we found, even if it was filtered.
                last_id = messages[-1].id
            else:
                # Attempt to set the cache for subsequent requests. But
                # don't go above the message_id we checked, in case
                # there is a new message just now.
                last_id = None
                messages = list(Message.objects.filter(channel__id=channel_id,
                                                       id__lte=message_id)
                                .order_by('-id')[0:1])
                if len(messages):
                    last_id = messages[0].id

            if last_id is not None:
                cache.set(cache_key, last_id, CACHE_TIME)

    return JsonResponse(request, json, compact=True)
