from django.dispatch import Signal


# Connect to this if you want to know when a new incoming TextMessage
# arrives through the specific backend API.
#
# The SMS backends guarantee guarantee that on incoming message and on
# message appending, this signal is fired.
#
# Yes, you could connect to the TextMessage post_save signal, and when
# created is True it is the same as listening to the first firing of
# this signal. When a second part of a text message comes in and is
# appended to the original, the created boolean will be False and you
# cannot know for sure whether there was a new message someone was just
# editing the TextMessage.
#
# The instance argument holds the Text Message, the appended boolean
# tells whether this was a new (False) or an existing message that was
# appended to (True).
incoming_message = Signal(providing_args=('instance', 'appended'))
