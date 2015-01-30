# vim: set ts=8 sw=4 sts=4 et ai:
# We also remove the calls to long() in favor of calls to int() because
# the former is gone in python3.
if 0xffffffff == -1:
    raise NotImplementedError()

import urllib
import urllib2

from osso.aboutconfig.utils import aboutconfig
from osso.sms import BaseSmsBackend, BackendError
from osso.sms.models import TextMessageExtra

try:
    from osso.autolog.utils import log
except ImportError:
    log = lambda *x, **y: None


class ZjipzSmsBackend(BaseSmsBackend):
    def send_messages(self, sms_messages, reply_to=None,
                      shortcode_keyword=None, tariff_cent=None):
        sent = 0
        for message in sms_messages:
            if self.send_sms(message, reply_to=reply_to,
                             shortcode_keyword=shortcode_keyword,
                             tariff_cent=tariff_cent):
                sent += 1
        return sent

    def send_sms(self, message, reply_to=None, shortcode_keyword=None,
                 tariff_cent=None):
        '''
        Send SMS to gsmrelay.smswebapp.nl.
        '''
        # Special hacks here. We use +0 as the bogus address. If it is
        # set, someone else will be polling this message from us using
        # some other identifier.
        if message.remote_address == '+0':
            message.status = 'pnd'
            message.save()
            return True

        zjipz_submit_sms_url = \
            aboutconfig('sms.backends.sms_zjipz.url').encode('utf-8')
        assert zjipz_submit_sms_url  # raise backenderror?
        zjipz_submit_sms_url = ('%s?service={service}&body={body}'
                                '&local_address={local_address}'
                                '&remote_address={remote_address}'
                                '&tariff_cent={tariff_cent}'
                                '&reply_to={reply_to}' %
                                (zjipz_submit_sms_url,))

        if reply_to:
            try:
                reply_to = reply_to.extra.foreign_reference
            except TextMessageExtra.DoesNotExist:
                log(('warning: replying to message that we did not get '
                     'through this backend (msg=%d, reply_to=%d)') %
                    (message.id, reply_to.id),
                    log='sms', subsys='zjipz-out', fail_silently=True)
                reply_to = ''
        else:
            reply_to = ''

        tariff_cent = int(tariff_cent or 0)
        if tariff_cent:
            assert len(message.local_address) == 4

        parameters = {
            'service': aboutconfig('sms.backends.sms_zjipz.service'),
            'body': message.body,
            'local_address': message.local_address,
            'remote_address': message.remote_address,
            'tariff_cent': tariff_cent,
            'reply_to': reply_to,
        }
        log('data: %r' % (parameters,), log='sms', subsys='zjipz-out',
            fail_silently=True)
        for k, v in parameters.items():
            parameters[k] = urllib.quote(unicode(v).encode('utf-8'))

        url = zjipz_submit_sms_url.format(**parameters)
        log('url: %r' % (url,), log='sms', subsys='zjipz-out',
            fail_silently=True)

        fp = None
        success = False
        try:
            fp = urllib2.urlopen(url)
            response = fp.read()
            success = True
        except urllib2.HTTPError as e:
            response = '%r: %s' % (e, e)
            fp = e.fp  # see finally clause
        except Exception as e:
            response = '%r: %s' % (e, e)
        finally:
            if fp:
                # Try a bit harder to flush the connection and close it
                # properly. In case of errors, our django testserver peer
                # will show an error about us killing the connection
                # prematurely instead of showing the URL that causes the
                # error. Flushing the data here helps.
                data = fp.read()
                fp.close()
                del data

        # Log result
        log('result: %s' % response, log='sms', subsys='zjipz-out',
            fail_silently=True)

        # Success is relative
        success = success and response.startswith('OK')

        if success:
            remote_id = int(response.split(' ')[1])
            message.status = 'pnd'
            message.save()
            extra, created = TextMessageExtra.objects.get_or_create(
                textmessage=message,
                defaults={
                    'tariff_cent': int(tariff_cent),
                    'foreign_reference': str(remote_id),
                }
            )
            if not created:
                extra.update(foreign_reference=str(remote_id))
        else:  # no success
            if not self.fail_silently:
                raise BackendError('Failed to send SMS. '
                                   'Remote end-point failed us.')
            message.status = 'nak'
            message.save()
        return success
