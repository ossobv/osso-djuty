# vim: set ts=8 sw=4 sts=4 et ai:
import http.client
import urllib.request, urllib.parse, urllib.error
import urllib.request, urllib.error, urllib.parse
import socket
import ssl
import sys


class BadProtocol(ValueError):
    """
    Raised when you try to http_get or http_post with a disallowed
    protocol.
    """
    pass


class HTTPError(urllib.error.HTTPError):
    """
    Override the original HTTPError, drop the fp and add a response.
    """
    def __init__(self, url, code, msg, hdrs, response):
        urllib.error.HTTPError.__init__(self, url, code, msg, hdrs, None)
        self.response = response

    def __str__(self):
        assert isinstance(self.response, str)
        response = self.response[0:512] + ('', '...')[len(self.response) > 512]
        response = ''.join(('?', i)[0x20 <= ord(i) <= 0x7F or i in '\t\n\r']
                           for i in response)
        return ('HTTPError: """%s %s\nContent-Type: %s\n'
                'Content-Length: %d\n\n%s"""' %
                (self.code, self.msg, self.hdrs.type, len(self.response),
                 response))


class Options(object):
    # Which protocols to we allow.
    protocols = ('http', 'https')
    # Do we validate the SSL certificate.
    verify_cert = False
    # What we use to validate the SSL certificate.
    cacert_file = '/etc/ssl/certs/ca-certificates.crt'
    # Optional headers.
    headers = None
    # Timeout.
    timeout = 120

    # Which properties we have.
    _PROPERTIES = (
        'protocols', 'verify_cert', 'cacert_file', 'headers',
        'timeout')

    def __init__(self, **kwargs):
        for key, value in list(kwargs.items()):
            if key not in self._PROPERTIES:
                raise TypeError('unexpected arg %r' % (key,))
            setattr(self, key, value)

    def __or__(self, other):
        """
        Join multiple Options together with the or-operator '|'.
        It uses the identity operator to compare values against the
        default values, so non-overridden values won't overwrite
        overridden ones.

        BUG: This will fail if you try to re-set booleans from False
        to True to False.
        """
        new_options = Options()

        for source in (self, other):
            for item in self._PROPERTIES:
                source_item = getattr(source, item)
                if source_item is not getattr(Options, item):  # identity check
                    setattr(new_options, item, source_item)

        return new_options

# Default options.
opt_default = Options()

# SSL-safe options.
opt_secure = Options()
opt_secure.protocols = ('https',)
opt_secure.verify_cert = True


class Request(urllib.request.Request):
    """
    Override the urllib2.Request class to supply a custom method.
    """
    def __init__(self, method=None, *args, **kwargs):
        urllib.request.Request.__init__(self, *args, **kwargs)
        assert method in ('DELETE', 'GET', 'POST', 'PUT')
        self._method = method

    def get_method(self):
        return self._method


class ValidHTTPSConnection(http.client.HTTPConnection):
    """
    This class allows communication via SSL.

    Originally by: Walter Cacau, 2013-01-14
    Source: http://stackoverflow.com/questions/6648952/\
            urllib-and-validation-of-server-certificate
    """
    default_port = http.client.HTTPS_PORT
    cacert_file = opt_default.cacert_file

    def __init__(self, *args, **kwargs):
        http.client.HTTPConnection.__init__(self, *args, **kwargs)

    def connect(self):
        "Connect to a host on a given (SSL) port."
        sock = socket.create_connection(
            (self.host, self.port), self.timeout, self.source_address)
        if self._tunnel_host:
            self.sock = sock
            self._tunnel()
        self.sock = ssl.wrap_socket(
            sock, ca_certs=self.cacert_file,
            cert_reqs=ssl.CERT_REQUIRED)


class ValidHTTPSHandler(urllib.request.HTTPSHandler):
    """
    Originally by: Walter Cacau, 2013-01-14
    Source: http://stackoverflow.com/questions/6648952/\
            urllib-and-validation-of-server-certificate
    """
    def __init__(self, cacert_file):
        self.cacert_file = cacert_file
        urllib.request.HTTPSHandler.__init__(self)

    def https_open(self, req):
        # If someone uses an alternate cacert_file, we have no decent
        # way of telling that to a subclass (not instance).
        if self.cacert_file == ValidHTTPSConnection.cacert_file:
            class_ = ValidHTTPSConnection
        else:
            # Yuck. Create a local subclass so we can set a custom
            # cacert_file.
            class CustomValidHTTPSConnection(ValidHTTPSConnection):
                cacert_file = self.cacert_file
            class_ = CustomValidHTTPSConnection

        return self.do_open(class_, req)


def http_delete(url, opt=opt_default):
    '''
    Shortcut for urlopen (DELETE) + read.
    '''
    return _http_request(url, method='DELETE', opt=opt)


def http_get(url, opt=opt_default):
    '''
    Shortcut for urlopen (GET) + read.
    '''
    return _http_request(url, method='GET', opt=opt)


def http_post(url, data=None, opt=opt_default):
    '''
    Shortcut for urlopen (POST) + read.
    '''
    if isinstance(data, str):
        # Allow binstrings for data.
        pass
    elif data:
        data = urllib.parse.urlencode(data)
    else:
        data = ''  # ensure POST-mode
    return _http_request(url, method='POST', data=data, opt=opt)


def http_put(url, data=None, opt=opt_default):
    '''
    Shortcut for urlopen (PUT) + read.
    '''
    if isinstance(data, str):
        # Allow binstrings for data.
        pass
    elif data:
        data = urllib.parse.urlencode(data)
    else:
        data = ''  # ensure POST-mode
    return _http_request(url, method='PUT', data=data, opt=opt)


def _http_request(url, method=None, data=None, opt=None):
    # Check protocol.
    proto = url.split(':', 1)[0]
    if proto not in opt.protocols:
        raise BadProtocol('Protocol %s in URL %r disallowed by caller' %
                          (proto, url))

    # Create URL opener.
    if opt.verify_cert:
        # It's legal to pass either a class or an instance here.
        opener = urllib.request.build_opener(ValidHTTPSHandler(opt.cacert_file))
    else:
        opener = urllib.request.build_opener()

    # Create the Request with optional extra headers.
    req = Request(
        url=url, data=data, method=method, headers=(opt.headers or {}))

    exc_info, fp = None, None
    try:
        # (docs say first arg is 'url', but it is 'fullurl')
        fp = opener.open(req, timeout=opt.timeout)
        # print fp.info()  # (temp, print headers)
        response = fp.read()
    except urllib.error.HTTPError as exception:
        fp = exception.fp  # see finally clause
        exc_info = sys.exc_info()
    except Exception:
        exc_info = sys.exc_info()
    finally:
        if fp:
            # Try a bit harder to flush the connection and close it
            # properly. In case of errors, our django testserver peer
            # will show an error about us killing the connection
            # prematurely instead of showing the URL that causes the
            # error. Flushing the data here helps.
            if exc_info:
                response = fp.read()
                fp.close()
                # And, even more importantly. Some people want the
                # exception/error info. Store it in our HTTPError
                # subclass.
                raise HTTPError(
                    exc_info[1].url,
                    exc_info[1].code,
                    exc_info[1].msg,
                    exc_info[1].hdrs,
                    response
                )
            fp.close()

    if exc_info:
        raise  # exc_info[0], exc_info[1], exc_info[2]
    return response


if __name__ == '__main__':
    # Test the Options or-operator.
    print('Testing OPTIONS')
    a = Options()
    a.protocols = ('ftp',)
    a.cacert_file = 'overwrite_me'
    b = Options()
    b.cacert_file = '/tmp/test.crt'
    c = a | b
    assert c.protocols == ('ftp',)
    assert c.verify_cert is False
    assert c.cacert_file is '/tmp/test.crt'

    a = (opt_secure | Options(timeout=10))
    assert a.protocols == ('https',)
    assert a.timeout == 10

    # Test basic HTTP-get.
    print('Testing BASIC http_get')
    try:
        http_get('http://example.com/get')
    except HTTPError as e:
        print(('Got %s' % (e,)))
    else:
        assert False, 'expected 404'

    # Test other HTTP methods.
    # print('Testing BASIC http_post/http_put/http_delete')
    # http_post('http://example.com/get')     # this URL doesn't mind a POST
    # http_put('http://example.com/get')      # this URL doesn't mind a PUT
    # http_delete('http://example.com/get')   # this URL doesn't mind a DELETE

    # Test error documents.
    # print('Testing response fetching of error documents')
    # try:
    #     http_get('http://example.com/502.html')
    # except HTTPError as e:
    #     assert isinstance(e, urllib2.HTTPError)
    #     assert e.response.find('</html>') != -1
    # else:
    #     assert False, '502.html did not raise HTTPError'

    # Test that HTTPS fails in secure mode.
    print('Testing SECURE-only http_get')
    try:
        http_get('http://example.com', opt=opt_secure)
    except BadProtocol:
        pass
    else:
        assert False, 'Protocol check did not raise BadProtocol!'

    # Domain with bad cert.
    # bad_cert_url = 'https://bad.cert.example.com/'

    # Test that HTTPS does a proper check.
    print('Testing HTTPS http_get')
    http_get('https://example.com/')     # good cert
    # http_get('https://216.58.212.206/')  # bad cert, but don't care

    print('Testing HTTPS-secure http_get')
    http_get('https://example.com/', opt=opt_secure)
    # try:
    #     http_get(bad_cert_url, opt=opt_secure)
    # except urllib2.URLError:
    #     pass  # ok!
    # else:
    #     assert False, ('We did not catch the bad certificate of %r' %
    #                   (bad_cert_url,))
