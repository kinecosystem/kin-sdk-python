# -*- coding: utf-8 -*

# Copyright (C) 2018 Kin Foundation

from stellar_base.asset import Asset

from .version import __version__


KIN_ISSUER_PROD = 'GDVDKQFP665JAO7A2LSHNLQIUNYNAAIGJ6FYJVMG4DT3YJQQJSRBLQDG'  # TODO: real address
KIN_ASSET_PROD = Asset('KIN', KIN_ISSUER_PROD)

KIN_ISSUER_TEST = 'GCKG5WGBIJP74UDNRIRDFGENNIH5Y3KBI5IHREFAJKV4MQXLELT7EX6V'
KIN_ASSET_TEST = Asset('KIN', KIN_ISSUER_TEST)

# https://www.stellar.org/developers/guides/concepts/fees.html
BASE_RESERVE = 0.5  # in XLM
MIN_ACCOUNT_BALANCE = (2 + 1) * BASE_RESERVE  # 1 additional trustline op

SDK_USER_AGENT = 'kin-stellar-python/{}'.format(__version__)
