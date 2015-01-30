'''
Meeting app

Depends on osso.sms with a valid SMS_BACKEND setting

# meeting app settings
# the phone number should not be longer then 9 characters
# otherwise the sms message will be truncated
MEETING_PHONE_NUMBER = '0900 OSSO'

MEETING_SMS_SHORTCODE = '1234'
MEETING_SMS_MAX_LENGTH = 160

# the originator which is visible by the receiver
# numeric: 16 digits max
# alphanumeric: 11 characters max
MEETING_SMS_ORIGINATOR = 'OSSO'

# keywords used to confirm or decline a invitation
MEETING_SMS_KEYWORD_CONFIRM = 'YES'
MEETING_SMS_KEYWORD_DECLINE = 'NO'
'''
