# vim: set ts=8 sw=4 sts=4 et ai:
#
# Example usage of filters:
#
#     def operators_dont_see_status_messages(message, channel_id=None,
#                                            group_ids=None):
#         '''
#         A filter that prohibits "pure" operators from seeing status
#         messages (the messages with no sender) in their user chat.
#         '''
#         # (Bad example that uses hardcoded group names :P )
#         if message.sender is None and group_ids == [5]:
#             return None
#         return message
#     pre_send_add(operators_dont_see_status_messages)


# Where we store the filters.
_pre_send_filters = []


def pre_send_add(filter):
    assert filter not in _pre_send_filters
    _pre_send_filters.append(filter)


def pre_send_run(message, channel_id=None, group_ids=None):
    for filter in _pre_send_filters:
        message = filter(message, channel_id=channel_id, group_ids=group_ids)
        if message is None:
            return None
    return message
