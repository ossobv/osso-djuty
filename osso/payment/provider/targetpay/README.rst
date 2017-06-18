Fetched::

* 2016-09-04: https://www.targetpay.com/docs/TargetPay_iDEAL_V3.0_nl.pdf
* 2016-09-04: https://www.targetpay.com/info/bankwire-docu "TargetPay_bankwire-docu.html"
* 2016-09-04: https://www.targetpay.com/docs/TargetPay_MisterCash_V1.2_nl.pdf
* 2017-06-17: https://www.targetpay.com/info/cc-docu "TargetPay_creditcard-docu.html"
* 2017-06-18: https://www.targetpay.com/info/cc-docu-atos "TargetPay_creditcard-atos-docu.html"

Example URL for iDEAL::

    https://www.targetpay.com/ideal/start?\
      rtlo=$NUMBER&description=test123&amount=123&\
      returnurl=https://$HOST/return&\
      cancelurl=https://$HOST/cancel&\
      reporturl=https://$HOST/report&test=1&ver=3
    >>> 000000 177XXX584|https://www.targetpay.com/ideal/launch?trxid=177XXX584&ec=779XXXXXXXXX273

    https://www.targetpay.com/ideal/launch?trxid=177XXX584&ec=779XXXXXXXXX273
    >>> ... returns to https://$HOST/return?trxid=177XXX584&idealtrxid=003XXXXXXXXXX497&ec=779XXXXXXXXX273
