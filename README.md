osso-djuty
==========

[![Continuous Integration Status](https://travis-ci.org/ossobv/osso-djuty.svg?branch=python3)](https://travis-ci.com/github/ossobv/osso-djuty)

A bunch of Django utility functions / helpers.

> **Note**: The python3 branch is a super slimmed down version with several
>           apps removed in order to move the code forwards. You can still
>           use the old apps by switching to the [master][master] or
>           [django14-18][django14-18] branch.


Contents
--------

| module       | description                                               |
|--------------|-----------------------------------------------------------|
| aboutconfig  | Get/set basic settings from DB/cache.                     |
| core         | Lots of nice Django stuff.                                |
| l10n         | Localization utilities. Note the templatetag is l10n_o    |
| mysql        | MySQL fields.                                             |
| rpc          | RPC through jsonrpc and xmlrpc helpers.                   |
| sequence     | Unique incremental IDs for various databases.             |
| xhr          | JsonResponse helper.                                      |


| other       | description       |
|-------------|-------------------|
| doc         | Schema dump tool. |
| locale      | Locale files.     |


[django14-18]: https://github.com/ossobv/osso-djuty/tree/django14-18
[master]: https://github.com/ossobv/osso-djuty/tree/master
