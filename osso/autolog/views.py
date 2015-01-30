# vim: set ts=8 sw=4 sts=4 et ai:
import mimetypes # fix against missing .log mimetype
from django.conf import settings
from django.contrib.auth import REDIRECT_FIELD_NAME
from django.contrib.auth.decorators import login_required
from django.http import HttpResponseRedirect
from django.utils.http import urlquote
from django.views.static import serve
from osso.autolog.utils import _logpath


def suserve(request, path, login_url=None, redirect_field_name=REDIRECT_FIELD_NAME):
    if not request.user.is_superuser:
        login_url = login_url or settings.LOGIN_URL
        path = urlquote(request.get_full_path())
        tup = login_url, redirect_field_name, path
        return HttpResponseRedirect('%s?%s=%s' % tup)

    try:
        mimetypes.types_map['.log']
    except KeyError:
        mimetypes.init()
        mimetypes.types_map['.log'] = 'text/plain'

    return serve(request, path, document_root=_logpath())
