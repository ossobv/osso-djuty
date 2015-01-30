# vim: set ts=8 sw=4 sts=4 et ai:


def get_active_relation(request, allow_id=False):
    # No user? No relation.
    if not hasattr(request, 'user'):
        #assert hasattr(request, 'user'), "The OSSO relation middleware requires authentication middleware to be installed. Edit your MIDDLEWARE_CLASSES setting to insert 'django.contrib.auth.middleware.AuthenticationMiddleware'."
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
        profile = request.user.get_profile()
    except ObjectDoesNotExist:
        return None
    # Return
    if allow_id:
        return profile.relation_id
    return profile.relation


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
