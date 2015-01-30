# vim: set ts=8 sw=4 sts=4 et ai:
import hashlib, time, urllib, urllib2
from osso.aboutconfig.utils import aboutconfig
from osso.sms import BaseSmsBackend


WIRELESS_API_VERSION = '1.1'
API_VERSION = 'osso.sms-1.0'

REQUEST_TYPE_BALANCE = 'BALANCE'
REQUEST_TYPE_BINARY = 'BINARY'
REQUEST_TYPE_GROUP_ICON = 'GROUP_ICON'
REQUEST_TYPE_MMS = 'MMS'
REQUEST_TYPE_PSMS = 'TEXT_MESSAGE_RB'
REQUEST_TYPE_OPERATOR_LOGO = 'OPERATOR_LOGO'
REQUEST_TYPE_OTA = 'OTA'
REQUEST_TYPE_PICTURE_MESSAGE = 'PICTURE_MESSAGE'
REQUEST_TYPE_QUERY = 'QUERY'
REQUEST_TYPE_RINGTONE = 'RINGTONE'
REQUEST_TYPE_SMS = 'TEXT_MESSAGE'

GATEWAY_PATHS = {
    REQUEST_TYPE_BALANCE: '/getbalance',
    REQUEST_TYPE_BINARY: '/sendbin',
    REQUEST_TYPE_GROUP_ICON: '/sendpic',
    REQUEST_TYPE_MMS: '/sendmms',
    REQUEST_TYPE_OPERATOR_LOGO: '/sendpic',
    REQUEST_TYPE_OTA: '/sendota',
    REQUEST_TYPE_PICTURE_MESSAGE: '/sendpic',
    REQUEST_TYPE_QUERY: '/query',
    REQUEST_TYPE_RINGTONE: '/sendringtone',
    REQUEST_TYPE_SMS: '/sendsms',
    REQUEST_TYPE_PSMS: '/sendpsms',
}


class WirelessSmsBackend(BaseSmsBackend):
    def __init__(self, *args, **kwargs):
        super(WirelessSmsBackend, self).__init__(*args, **kwargs)
        self.url = aboutconfig('sms.backends.sms_wireless.url', 'http://gateway.wireless-services.nl/').rstrip('/').encode('utf-8')
        self.backup_url = aboutconfig('sms.backends.sms_wireless.backup_url', 'http://gateway2.wireless-services.nl/').rstrip('/').encode('utf-8')
        self.password = aboutconfig('sms.backends.sms_wireless.password').encode('utf-8')
        self.batch_prefix = aboutconfig('sms.backends.sms_wireless.batch_prefix').encode('utf-8')
        self.default_args = {
            'API': API_VERSION,
            'AUTHTYPE': 'sha1',
            'TEST': aboutconfig('sms.backends.sms_wireless.test', '0').encode('utf-8'),
            'UID': aboutconfig('sms.backends.sms_wireless.username').encode('utf-8'),
            'VERSION': WIRELESS_API_VERSION,
            'ONUM': 1, # 0 is international number or 1 is national shortcode
            'NOT': '1', # enable notification request
            'MSGID': aboutconfig('sms.backends.sms_wireless.message_id').encode('utf-8'),
        }

    def send_messages(self, sms_messages, reply_to=None, shortcode_keyword=None, tariff_cent=None):
        sent = 0
        for message in sms_messages:
            if self.send_sms(message, reply_to=reply_to, tariff_cent=tariff_cent):
                sent += 1
        return sent

    def send_sms(self, message, reply_to=None, tariff_cent=None):
        is_premium = reply_to is not None

        append_meta = {}
        extra_args = {
            'BATCHID': '%s-%s' % (self.batch_prefix or 'default', message.id),
            'N': message.remote_address,
            'M': message.body,
            'O': message.local_address,
        }

        if is_premium:
            if tariff_cent is None:
                extra_args['RATE'] = int(aboutconfig('sms.backends.sms_wireless.tariff', 40))
            else:
                extra_args['RATE'] = tariff_cent
            # session_id is required for the kickback fee if available
            session_id = _get_wireless_session_id(reply_to)
            if session_id is not None:
                append_meta['wireless_session_id'] = session_id
                extra_args['SESSIONID'] = session_id
            # operator is required for the kickback fee if available
            if reply_to.remote_operator is not None:
                extra_args['OPR'] = reply_to.remote_operator.entire_code('')
                message.remote_operator = reply_to.remote_operator
            sent, info = self.request(REQUEST_TYPE_PSMS, extra_args)
        else:
            # message concatenation is only available for normal SMS
            # otherwise the receiver would be billed tariff_cent for each
            # received message
            # can't imagine why, isn't that the whole purpose of this business?
            if len(message.body) > 160:
                extra_args['CONCAT'] = '1'
            sent, info = self.request(REQUEST_TYPE_SMS, extra_args)

        append_meta['wireless_response'] = info

        if sent:
            message.status = 'pnd'
        else:
            message.status = 'nak'

        message.meta_append(append_meta, commit=False)
        message.save()
        return sent

    def request(self, request_type, extra_args=None):
        '''
        Send a request of type ``request_type`` to the SMS gateway
        '''
        # determine the request path for the request type
        if request_type not in GATEWAY_PATHS:
            raise ValueError('Invalid request type %r' % request_type)
        request_path = GATEWAY_PATHS.get(request_type)
        # setup the authentication parameters
        args = self.default_args.copy()
        auth_time = '%d' % time.time()
        args.update({
            'AUTHTIME': auth_time,
            'PWD': hashlib.sha1('%s%s' % (self.password, auth_time)).hexdigest(),
        })
        if extra_args is not None:
            args.update(extra_args)
        urlencoded_args = urllib.urlencode(args)

        for url in (self.url, self.backup_url):
            if not url:
                continue
            try:
                f = urllib2.urlopen('%s%s' % (url, request_path), urlencoded_args)
                response = f.read()
                # response: <code>=<info>
                code, info = response.split('=', 2)
                # code=0XX: message accepted, XX sent
                # info: batch id
                if code.startswith('0'):
                    return True, info
                # code 1XX: invalid/error/nocredits
                # info: error message
                if code.startswith('1'):
                    return False, '%s: %s' % (code, info)
                # code 200: internal error, try again on the next server
                if code == '200':
                    continue
            except urllib2.URLError:
                # server unavailable, try the next server
                continue

        if not self.fail_silently:
            raise ValueError('SMS gateway: not available')
        return False, 'SMS gateway: not available'


def _get_wireless_session_id(text_message):
    '''
    Fetch wireless_session_id value from the metadata.

    Note that as of februari 2010, there is no provisioning for setting
    this value at all. It seems to only be used some countries, not in
    the Netherlands. So, this will probably return None all the time :)
    '''
    meta = text_message.meta
    if meta is not None:
        session_ids = [i['wireless_session_id'] for i in meta if 'wireless_session_id' in i]
        if len(session_ids) == 1:
            return session_ids[0]
    return None
