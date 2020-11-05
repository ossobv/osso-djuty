# vim: set ts=8 sw=4 sts=4 et ai:
from .ronald_koebler_jsonrpc import RPCError as Error; Error # put in this scope
import urllib.request, urllib.error, urllib.parse
from . import ronald_koebler_jsonrpc


class HttpCookieTransport(ronald_koebler_jsonrpc.Transport):
    def __init__(self, url):
        ronald_koebler_jsonrpc.Transport.__init__(self)
        self.url = url
        self.cookie = None
        self.to_recv = []

    def send(self, data):
        exception, fp = None, None
        headers = {'Content-Type': 'application/json'}
        if self.cookie:
            headers['Cookie'] = self.cookie
        try:
            req = urllib.request.Request(self.url, data, headers)
            fp = urllib.request.urlopen(req)
            response = fp.read()
        except urllib.error.HTTPError as exception:
            fp = exception.fp # see finally clause
        except Exception as exception:
            pass
        finally:
            if fp:
                # Try a bit harder to flush the connection and close it
                # properly.
                if exception:
                    response = fp.read()
                # Get cookie headers if available.
                self.cookie = fp.headers.get('set-cookie') or self.cookie
                fp.close()
        if exception:
            raise exception
        self.to_recv.append(response)

    def recv(self):
        try:
            data = self.to_recv.pop(0)
        except IndexError:
            return ''
        else:
            return data


class ServerProxy(ronald_koebler_jsonrpc.ServerProxy):
    def __init__(self, url):
        version = ronald_koebler_jsonrpc.JsonRpc10()
        transport = HttpCookieTransport(url)
        ronald_koebler_jsonrpc.ServerProxy.__init__(self, version, transport)
