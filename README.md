osso-djuty
==========

A bunch of Django utility functions / helpers.

> **Note**: The master branch is a slimmed down version with several apps removed
>           in order to move the code forwards. You can still use the old apps by
>           switching to the [django14-18][django14-18] branch.


Contents
--------

| module       | description                                               |
|--------------|-----------------------------------------------------------|
| aboutconfig  | Get/set basic settings from DB/cache.                     |
| autolog      | Crappy alternative to proper `logging`.                   |
| core         | Lots of nice Django stuff.                                |
| l10n         | Localization utilities.                                   |
| mysql        | MySQL fields.                                             |
| payment      | Payment modules for Mollie, MultiSafePay, Paypal, Sofort. |
| relation     | Relation, address and contacts.                           |
| rpc          | RPC through jsonrpc and xmlrpc helpers.                   |
| search       | Saving keywords from fields for easy searching.           |
| sequence     | Unique incremental IDs for various databases.             |
| sms          | SMS modules for Mollie and Wireless.                      |
| useractivity | Keeping track of logins/logouts.                          |
| userchat     | Simple chat multiuser through a cached polling interface. |
| videmus      | Video conversion modules and routines.                    |
| xhr          | JsonResponse helper.                                      |


| other       | description       |
|-------------|-------------------|
| doc         | Schema dump tool. |
| locale      | Locale files.     |


[django14-18]: https://github.com/ossobv/osso-djuty/tree/django14-18
