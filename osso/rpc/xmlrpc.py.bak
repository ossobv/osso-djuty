# vim: set ts=8 sw=4 sts=4 et ai:
import urlparse, xmlrpclib
from xmlrpclib import Error, ProtocolError; Error # put in this scope

import logging
logger = logging.getLogger('osso.rpc')


class CookieTransportHelper:
    def __init__(self, parent_transport):
        self.parent = parent_transport
        self.parent.__init__(self)
        self.cookie = None

    def send_host(self, connection, host):
        self.parent.send_host(self, connection, host)
        logger.debug('CookieTransportHelper, send_host=%s, cookie=%s' %
                     (host.encode('utf-8'), self.cookie))
        if self.cookie:
            connection.putheader('Cookie', self.cookie)

    #
    # In python 2.6 and older we have to overload request()
    #
    if hasattr(xmlrpclib.Transport, '_parse_response'):
        def request(self, host, handler, request_body, verbose=0):
            h = self.make_connection(host)
            if verbose:
                h.set_debuglevel(1)

            self.send_request(h, handler, request_body)
            self.send_host(h, host)
            self.send_user_agent(h)
            self.send_content(h, request_body)

            errcode, errmsg, headers = h.getreply()

            if errcode != 200:
                raise ProtocolError(host + handler, errcode, errmsg, headers)

            self.verbose = verbose

            try:
                sock = h._conn.sock
            except AttributeError:
                sock = None

            # ADDED
            self.cookie = headers.get('set-cookie') or self.cookie
            logger.debug('CookieTransportHelper, request, cookie=%s' %
                         (self.cookie,))
            # END ADDED

            return self._parse_response(h.getfile(), sock)

    #
    # In python 2.7 and newer we can to overload parse_response()
    #
    else:
        def parse_response(self, response):
            self.cookie = response.getheader('set-cookie') or self.cookie
            logger.debug('CookieTransportHelper, parse_response, cookie=%s' %
                         (self.cookie,))
            return self.parent.parse_response(self, response)

class CookieTransport(CookieTransportHelper, xmlrpclib.Transport):
    def __init__(self):
        CookieTransportHelper.__init__(self, xmlrpclib.Transport)

class SafeCookieTransport(CookieTransportHelper, xmlrpclib.SafeTransport):
    def __init__(self):
        CookieTransportHelper.__init__(self, xmlrpclib.SafeTransport)


class ServerProxy(xmlrpclib.ServerProxy):
    def __init__(self, url):
        parts = urlparse.urlparse(url)
        if parts.scheme == 'https':
            transport = SafeCookieTransport()
        else:
            transport = CookieTransport()
        # Using use_datetime=True because Django will not auto-convert the
        # XMLRPC DateTime objects to a usable time.
        xmlrpclib.ServerProxy.__init__(self, url, transport=transport,
                                       use_datetime=True)
