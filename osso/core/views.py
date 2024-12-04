# vim: set ts=8 sw=4 sts=4 et ai:
from django.conf import settings
from django.core.mail import mail_admins
from django.http import HttpResponse, HttpResponseServerError
from django.template.loader import render_to_string
from django.utils.encoding import force_str
from django.utils.html import escape


__all__ = ('HttpFormResponse', 'HttpFormResponseError',
           'get_minimal_context', 'handler500', 'simple_form_view')


class HttpFormResponse(HttpResponse):
    def __init__(self, message='', saved=None, **kwargs):
        super(HttpFormResponse, self).__init__(content=message)


class HttpFormResponseError(HttpResponseServerError):
    def __init__(self, message='An error occurred', **kwargs):
        super(HttpFormResponseError, self).__init__(content=message)


def get_minimal_context():
    '''
    Fill the context with the bare minimum to be able to show a decent
    looking page.
    '''
    context = {}
    for key in ('MEDIA_URL',):
        context[key] = getattr(settings, key)
    return context


def handler500(request):
    '''
    Show an error response page.
    '''
    return HttpResponseServerError(render_to_string('500.html',
                                                    get_minimal_context()))


def simple_form_view(request, form_class, form_kwargs={}, heading='Form',
                     ip_whitelist=None, httpresponse_ok=HttpFormResponse,
                     httpresponse_fail=HttpFormResponseError,
                     mail_on_fail=False):
    '''
    A simple view prototype suitable for HTTP API form submitting.

    Pameters are:
     * request = the view request parameter
     * form_class = the form to show or process (callable)
     * form_kwargs = optional arguments for the instantiation of the
       form instance
     * heading = an optional title used in the HTML display
     * ip_whitelist = an optional list of IPv4 addresses to match the
       request's remote address against
     * httpresponse_ok = http response object to be returned on success
       (callable, not compatible with HttpResponse anymore, see
       HttpFormResponse, takes the return value from form.save() as
       ``saved`` parameter)
     * httpresponse_fail = http response object to be returned on
       failure (callable, takes a string, see HttpFormResponseError)
     * mail_on_fail = whether to mail the admins on invalid form input
    '''
    # Optional IP whitelisting
    if ip_whitelist is not None and not settings.DEBUG:
        ip = request.META.get('REMOTE_ADDR', '')
        if ip.startswith('::ffff:'):
            ip = ip[7:]
        if ip not in ip_whitelist:
            return httpresponse_fail('IP %s not in allow list; '
                                     'use DEBUG mode?' % ip)

    # Does the request have data?
    if request.method == 'POST':
        data = request.POST
    elif len(request.GET):
        data = request.GET
    else:
        data = None

    # Decide whether to show a form or to process it.
    if data:
        form = form_class(data=data, **form_kwargs)
        if form.is_valid():
            return_value = form.save()
            return httpresponse_ok(message='', saved=return_value)
        if mail_on_fail:
            mail_admins(
                'Invalid input on "%s" form' % (force_str(heading),),
                ('Form validation failed for form %s with kwargs %r.\n\n'
                 'Host: %s\nPath: %s\nRemoteAddr: %s\n\nData: %r\n\n'
                 'Errors: %r\n') %
                (form_class.__name__, form_kwargs, request.META['HTTP_HOST'],
                 request.META['PATH_INFO'], request.META['REMOTE_ADDR'],
                 data, form.errors)
            )
        return httpresponse_fail(message=('Input validation failed: %r' %
                                          form.errors))
    else:
        form = form_class(**form_kwargs)

    return HttpResponse(_form(heading, request.META['PATH_INFO'], form))


def _html(title, body):
    return '''<!DOCTYPE html PUBLIC "-//W3C//DTD XHTML 1.0 Strict//EN" \
"http://www.w3.org/TR/xhtml1/DTD/xhtml1-strict.dtd">
<html xmlns="http://www.w3.org/1999/xhtml" lang="en" xml:lang="en">
<head>
  <title>%(title)s</title>
  <meta http-equiv="Content-Type" content="text/html; charset=UTF-8"/>
</head>
<body>
  <h1>%(title)s</h1>
  %(body)s
</body>
</html>''' % {'title': escape(title), 'body': body}


def _form(title, url, form):
    return _html(
        title,
        ('<form method="post" action="%s"><table>%s<tr><th></th>'
         '<td><input type="submit"/></td></table>') %
        (url, form.as_table())
    )
