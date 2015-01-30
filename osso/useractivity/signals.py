from django.dispatch import Signal


# Connect to this if you want to know when a user logs in.
#
# The sender will be the User model, the instance is the User instance
# and explicit tells the receiver whether the user used the login
# procedure or simply got active again using an already existing
# session.
#
# We send users, not user_pks because it's probably better to do one
# unnecessary query once (if no one wants the user) than many (if every
# receiver wants it).
#
# NB: This signal is sent after the user has logged in. It is too late
# to update anything that should be used on the page the user is about
# to see. The request object is available. The motd app uses that to set
# a "first_login" session variable which it checks on the next loaded
# page.
logged_in = Signal(providing_args=('instance', 'explicit', 'request'))

# Connect to this if you want to know when a user logs out.
# See the comments for the logged_out signal for more information.
logged_out = Signal(providing_args=('instance', 'explicit'))
