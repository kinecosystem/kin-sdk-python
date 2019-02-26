"""Contains the config for the Kin SDK"""
from kin_base.operation import ONE as KIN_DECIMAL_PRECISION

from .blockchain.environment import Environment

from .version import __version__

# Create default environments.
HORIZON_URI_PROD = 'https://horizon.kinfederation.com'
HORIZON_PASSPHRASE_PROD = 'Kin Mainnet ; December 2018'
PROD_ENVIRONMENT = Environment('PROD', HORIZON_URI_PROD, HORIZON_PASSPHRASE_PROD)

HORIZON_URI_TEST = 'https://horizon-testnet.kininfrastructure.com'
HORIZON_PASSPHRASE_TEST = 'Kin Testnet ; December 2018'
FRIENDBOT_URL_TEST = "http://friendbot-testnet.kininfrastructure.com"
TEST_ENVIRONMENT = Environment('TEST', HORIZON_URI_TEST, HORIZON_PASSPHRASE_TEST, FRIENDBOT_URL_TEST)

MEMO_CAP = 28
# Template version - app_id - free text
MEMO_TEMPLATE = '1-{}-'
# hardcoded id for anonymous users
ANON_APP_ID = 'anon'
# 3/4 letters/numbers
APP_ID_REGEX = '^[a-zA-Z0-9]{3,4}$'

MAX_RECORDS_PER_REQUEST = 200

SDK_USER_AGENT = 'kin-core-python/{}'.format(__version__)
