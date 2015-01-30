# vim: set ts=8 sw=4 sts=4 et ai:
import datetime, sys, threading
from osso.sms import BaseSmsBackend


class ConsoleSmsBackend(BaseSmsBackend):
    def __init__(self, *args, **kwargs):
        self.stream = kwargs.pop('stream', sys.stdout)
        self._lock = threading.RLock()
        super(ConsoleSmsBackend, self).__init__(*args, **kwargs)

    def send_messages(self, sms_messages, reply_to=None, shortcode_keyword=None, tariff_cent=None):
        self._lock.acquire()
        try:
            for message in sms_messages:
                self.stream.write('%r: %s\n' % (message, message))
                self.stream.write('%s\n' % message.body)
                self.stream.write('-' * 79)
                self.stream.write('\n')
                self.stream.flush()
                message.status = 'ack'
                message.delivery_date = datetime.datetime.now()
                message.save()
        except:
            if not self.fail_silently:
                raise
        finally: # in python2.5+ this is correctly reached after exceptions
            self._lock.release()
        return len(sms_messages)
