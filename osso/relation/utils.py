# vim: set ts=8 sw=4 sts=4 et ai:
from django.core.exceptions import ObjectDoesNotExist


def get_active_relation(request):
    # No user? No relation.
    if not hasattr(request, 'user'):
        return None
    # Anonymous user? No relation either.
    user = request.user
    if user.is_anonymous():
        return None
    # Emulated relation?
    relation = request.session.get('active_relation')
    if relation:
        return relation
    # Real relation?
    try:
        contact = request.user.authenticatablecontact
    except ObjectDoesNotExist:
        return None
    # Return
    return contact.relation


def set_active_relation(request, relation):
    # This function is used to emulate the active relation.
    # Set relation to None to undo the emulation.
    # You should redirect to a new page after calling this, otherwise
    # the user.active_relation may already have been set.
    if relation:
        relation.is_emulated = True
        request.session['active_relation'] = relation
    else:
        try:
            del request.session['active_relation']
        except KeyError:
            pass
