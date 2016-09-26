# vim: set ts=8 sw=4 sts=4 et ai:

# Payment/sofort settings
OSSO_PAYMENT = {
    'test_mode': True,
    # == THE STUFF BELOW THIS LINE IS DEPRECATED ==
    'provider': 'osso.payment.provider.mollie',
    # Using %s in these URLs is optional, they will be replaced with
    # the payment id.
    'success_url': '/payment_ok/',
    'abort_url': '/payment_failed/',
    'toosoon_url': '/payment_unknown/',
}

# Mollie payment settings:
# 'test_mode' above enables "mollie test" mode here.
OSSO_PAYMENT_MOLLIE = {
    'partner_id': '123',
    'profile_key': '456',  # optional
}

# MultiSafepay settings
OSSO_PAYMENT_MSP = {
    'account': 'ACCOUNT',
    'site_id': 'SITE_ID',
    'site_secure_code': 'SITE_CODE',
    'api_key': 'LONG_API_HASH_KEY_UNUSED_FOR_NOW',
}

# Paypal settings
OSSO_PAYMENT_PAYPAL = {
    'username': False,
    'password': False,
    'signature': False,
}

# Sofort payment settings:
# 'test_mode' above enables "fake" sofort mode here.
OSSO_PAYMENT_SOFORT = {
    'user_id': 'MY_USERID',
    'project_id': '123456',
    'api_key': 'MY_APIKEY',
    'project_password': 'MY_PASSWORD',  # used for success url validation
}

# Targetpay settings
OSSO_PAYMENT_TARGETPAY = {
    'rtlo': 'FIXMEF',
}
