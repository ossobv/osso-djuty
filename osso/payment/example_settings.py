# vim: set ts=8 sw=4 sts=4 et ai:

# Payment/sofort settings
OSSO_PAYMENT = {
    'provider': 'osso.payment.provider.mollie',
    'test_mode': True,
    # Using %s in these URLs is optional, they will be replaced with
    # the payment id.
    'success_url': '/payment_ok/',
    'abort_url': '/payment_failed/',
    'toosoon_url': '/payment_unknown/',
}

# Mollie payment settings:
# test_mode enables mollie test mode here
OSSO_PAYMENT_MOLLIE = {
    'partner_id': '123',
    'profile_key': '456', # optional
}

# Sofort payment settings:
# test_mode enables "fake" sofort mode here
OSSO_PAYMENT_SOFORT = {
    'user_id': 'MY_USERID',
    'project_id': '123456',
    'api_key': 'MY_APIKEY',
    # this password is used for internal success url validation
    'project_password': 'MY_PASSWORD',
}
