"""Contains the config for the Kin SDK"""

from .blockchain.environment import Environment

from .version import __version__

# Create default environments.
KIN_ISSUER_PROD = 'GDF42M3IPERQCBLWFEZKQRK77JQ65SCKTU3CW36HZVCX7XX5A5QXZIVK'
HORIZON_URI_PROD = 'https://horizon-ecosystem.kininfrastructure.com'
HORIZON_PASSPHRASE_PROD = 'Public Global Kin Ecosystem Network ; June 2018'
PROD_ENVIRONMENT = Environment('ECOSYSTEM', HORIZON_URI_PROD, HORIZON_PASSPHRASE_PROD, KIN_ISSUER_PROD)

KIN_ISSUER_TEST = 'GBC3SG6NGTSZ2OMH3FFGB7UVRQWILW367U4GSOOF4TFSZONV42UJXUH7'
HORIZON_URI_TEST = 'https://horizon-playground.kininfrastructure.com'
HORIZON_PASSPHRASE_TEST = 'Kin Playground Network ; June 2018'
FRIENDBOT_URL_TEST = "http://friendbot-playground.kininfrastructure.com"
TEST_ENVIRONMENT = Environment('PLAYGROUND', HORIZON_URI_TEST, HORIZON_PASSPHRASE_TEST,
                               KIN_ISSUER_TEST, FRIENDBOT_URL_TEST)

# https://www.stellar.org/developers/guides/concepts/fees.html
BASE_RESERVE = 0.5  # in XLM
MIN_ACCOUNT_BALANCE = (2 + 1) * BASE_RESERVE + 0.1  # 1 additional trustline op + fees
DEFAULT_FEE = 1e-05  # 0.0000100
MEMO_CAP = 28
# Template version - app_id - free text
MEMO_TEMPLATE = '1-{}-'
# hardcoded id for anonymous users
ANON_APP_ID = 'anon'
# 4 letters/numbers
APP_ID_REGEX = '^[a-zA-Z0-9]{4}$'

MAX_RECORDS_PER_REQUEST = 200

SDK_USER_AGENT = 'kin-core-python/{}'.format(__version__)
