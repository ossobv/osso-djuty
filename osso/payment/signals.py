# vim: set ts=8 sw=4 sts=4 et ai:
from django.dispatch import Signal


payment_updated = Signal(providing_args=['change'])
