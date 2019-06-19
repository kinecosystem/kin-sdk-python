from .config import TEST_ENVIRONMENT, PROD_ENVIRONMENT, SDK_USER_AGENT
from .client import KinClient
from .account import KinAccount
from . import errors as KinErrors
from .transactions import OperationTypes, decode_transaction
from .blockchain.keypair import Keypair
from .blockchain.environment import Environment

# Override kin_base user agent with the kin-sdk user agent
from kin_base import horizon
horizon.HEADERS['User-Agent'] = SDK_USER_AGENT
