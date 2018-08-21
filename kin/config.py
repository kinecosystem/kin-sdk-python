# -*- coding: utf-8 -*

# Copyright (C) 2018 Kin Foundation

from stellar_base.asset import Asset

from .version import __version__


KIN_ISSUER_PROD = 'GDF42M3IPERQCBLWFEZKQRK77JQ65SCKTU3CW36HZVCX7XX5A5QXZIVK'
KIN_ASSET_PROD = Asset('KIN', KIN_ISSUER_PROD)

KIN_ISSUER_TEST = 'GBC3SG6NGTSZ2OMH3FFGB7UVRQWILW367U4GSOOF4TFSZONV42UJXUH7'
KIN_ASSET_TEST = Asset('KIN', KIN_ISSUER_TEST)

# https://www.stellar.org/developers/guides/concepts/fees.html
BASE_RESERVE = 0.5  # in XLM
MIN_ACCOUNT_BALANCE = (2 + 1) * BASE_RESERVE  # 1 additional trustline op

SDK_USER_AGENT = 'kin-core-python/{}'.format(__version__)
