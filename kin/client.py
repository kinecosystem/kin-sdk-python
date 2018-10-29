"""Contains the KinClient class to interact with the blockchain"""

import requests

from .config import SDK_USER_AGENT, ANON_APP_ID, MAX_RECORDS_PER_REQUEST
from . import errors as KinErrors
from .blockchain.keypair import Keypair
from .blockchain.builder import Builder
from .blockchain.horizon import Horizon
from .monitors import SingleMonitor, MultiMonitor
from .transactions import OperationTypes, SimplifiedTransaction, RawTransaction, build_memo
from .account import KinAccount, AccountStatus
from .blockchain.horizon_models import AccountData
from .blockchain.utils import is_valid_address, is_valid_transaction_hash, is_valid_secret_key
from .version import __version__

import logging

logger = logging.getLogger(__name__)


class KinClient(object):
    """
    The :class:`kin.KinClient` class is the primary interface to the KIN Python SDK based on Kin Blockchain.
    It maintains a connection context with a Horizon node and hides all the specifics of dealing with Kin REST API.
    """

    def __init__(self, environment):
        """Create a new instance of the KinClient to query the Kin blockchain.
        :param `kin.Environment` environment: an environment for the client to point to.

        :return: An instance of the KinClient.
        :rtype: :class:`KinErrors.KinClient`
        """

        self.environment = environment
        self.network = environment.name

        # init our asset
        self.kin_asset = environment.kin_asset

        self.horizon = Horizon(horizon_uri=environment.horizon_uri, user_agent=SDK_USER_AGENT)
        logger.info('Kin SDK inited on network {}, horizon endpoint {}'.format(self.network, self.horizon.horizon_uri))

    def kin_account(self, seed, channels=None, channel_secret_keys=None, create_channels=False, app_id=ANON_APP_ID):
        """
        Create a new instance of a KinAccount to perform authenticated operations on the blockchain.
        :param str seed: The secret seed of the account that will be used
        :param int channels: Number of channels to use
        :param list of str channel_secret_keys: A list of seeds to be used as channels
        :param boolean create_channels: Should the sdk create the channel accounts
        :param str app_id: the unique id of your app
        :return: An instance of KinAccount
        :rtype: :class:`kin.KinAccount`

        :raises: :class:`KinErrors.AccountNotFoundError`: if SDK wallet or channel account is not yet created.
        :raises: :class:`KinErrors.AccountNotActivatedError`: if SDK wallet account is not yet activated.
        """

        # Create a new kin account, using self as the KinClient to be used
        return KinAccount(seed, self, channels, channel_secret_keys, create_channels, app_id)

    def get_config(self):
        """Get system configuration data and online status.
        :return: a dictionary containing the data
        :rtype: dict
        """
        status = {
            'sdk_version': __version__,
            'environment': self.environment.name,
            'kin_asset': {
                'code': self.kin_asset.code,
                'issuer': self.kin_asset.issuer
            },
            'horizon': {
                'uri': self.horizon.horizon_uri,
                'online': False,
                'error': None,
            },
            'transport': {
                'pool_size': self.horizon.pool_size,
                'num_retries': self.horizon.num_retries,
                'request_timeout': self.horizon.request_timeout,
                'retry_statuses': self.horizon.status_forcelist,
                'backoff_factor': self.horizon.backoff_factor,
            }
        }

        # now check Horizon connection
        try:
            self.horizon.query('')
            status['horizon']['online'] = True
        except Exception as e:
            status['horizon']['error'] = str(e)

        return status

    def get_account_balances(self, address):
        """
        Get the KIN and XLM balance of a given account
        :param str address: the public address of the account to query
        :return: a dictionary containing the balances
        :rtype: dict

        :raises: ValueError: if the provided address has the wrong format.
        :raises: :class:`KinErrors.AccountNotFoundError`: if the account does not exist.
        """
        account_data = self.get_account_data(address)
        balances = {}
        for balance in account_data.balances:
            if balance.asset_code == self.kin_asset.code and \
                            balance.asset_issuer == self.kin_asset.issuer:
                balances['KIN'] = balance.balance
            elif balance.asset_type == 'native':
                balances['XLM'] = balance.balance

        return balances

    def get_account_status(self, address):
        """
        Get a given account status
        :param str address: The public address of the account to query.
        :return: One the possible account statuses.
        :rtype: :enum:`kin.AccountStatus`
        """
        try:
            balances = self.get_account_balances(address)
        except KinErrors.AccountNotFoundError:
            return AccountStatus.NOT_CREATED

        try:
            balances['KIN']
        except KeyError:
            return AccountStatus.NOT_ACTIVATED

        return AccountStatus.ACTIVATED

    def get_account_data(self, address):
        """Get account data.

        :param str address: the public address of the account to query.

        :return: account data
        :rtype: :class:`kin.AccountData`

        :raises: ValueError: if the provided address has a wrong format.
        :raises: :class:`KinErrors.AccountNotFoundError`: if the account does not exist.
        """
        # TODO: might want to simplify the returning data
        if not is_valid_address(address):
            raise ValueError('invalid address: {}'.format(address))

        try:
            acc = self.horizon.account(address)
            return AccountData(acc, strict=False)
        except Exception as e:
            err = KinErrors.translate_error(e)
            raise KinErrors.AccountNotFoundError(address) if \
                isinstance(err, KinErrors.ResourceNotFoundError) else err

    def get_transaction_data(self, tx_hash, simple=True):
        """Gets transaction data.

        :param str tx_hash: transaction hash.
        :param boolean simple: (optional) returns a simplified transaction object

        :return: transaction data
        :rtype: :class:`kin.TransactionData` or `kin.SimplifiedTransaction`

        :raises: ValueError: if the provided hash is invalid.
        :raises: :class:`KinErrors.ResourceNotFoundError`: if the transaction does not exist.
        :raises: :class:`KinErrors.CantSimplifyError`: if the tx is too complex to simplify
        """
        if not is_valid_transaction_hash(tx_hash):
            raise ValueError('invalid transaction hash: {}'.format(tx_hash))

        try:
            raw_tx = RawTransaction(self.horizon.transaction(tx_hash))
        except Exception as e:
            raise KinErrors.translate_error(e)

        if simple:
            return SimplifiedTransaction(raw_tx, self.kin_asset)
        return raw_tx

    def get_account_tx_history(self, address, amount=10, descending=True, cursor=None, simple=True):
        """
        Get the transaction history for a given account.
        :param str address: The public address of the account to query
        :param int amount: The maximum number of transactions to get
        :param bool descending: The order of the transactions, True will start from the latest one
        :param int cursor: The horizon paging token
        :param bool simple: Should the returned txs be simplified, if True, complicated txs will be ignored
        :return: A list of transactions
        :rtype: list
        """

        if not is_valid_address(address):
            raise ValueError('invalid address: {}'.format(address))

        if amount <= 0:
            raise ValueError('Limit must be bigger than 0')

        tx_list = []

        requested_amount = amount if amount < MAX_RECORDS_PER_REQUEST else MAX_RECORDS_PER_REQUEST
        params = {
            'limit': requested_amount,
            'order': 'desc' if descending else 'asc'
        }

        # cursor is optional
        if cursor is not None:
            params['cursor'] = cursor

        horizon_response = self.horizon.account_transactions(address, params)

        for transaction in horizon_response['_embedded']['records']:
            raw_tx = RawTransaction(transaction)
            if simple:
                try:
                    simple_tx = SimplifiedTransaction(raw_tx, self.kin_asset)
                    tx_list.append(simple_tx)
                except KinErrors.CantSimplifyError:
                    pass
            else:
                tx_list.append(raw_tx)
            last_cursor = transaction['paging_token']

        remaining_txs = amount - len(tx_list)
        # if we got all the txs that we wanted, or there are no more txs
        if remaining_txs <= 0 or len(horizon_response['_embedded']['records']) < amount:
            return tx_list
        # If there are anymore transactions, recursively get the next transaction page
        return tx_list.extend(self.get_account_tx_history(address, remaining_txs, descending, last_cursor, simple))



    def verify_kin_payment(self, tx_hash, source, destination, amount, memo=None, check_memo=False, app_id=ANON_APP_ID):
        """
        Verify that a give tx matches the desired parameters
        :param str tx_hash: The hash of the transaction to query
        :param str source: The expected source account
        :param str destination: The expected destination account
        :param float amount: The expected amount
        :param str memo: (optional) The expected memo
        :param boolean check_memo: (optional) Should the memo match
        :param the id of the app that sent the tx
        :return: True/False
        :rtype: boolean
        """

        tx = self.get_transaction_data(tx_hash)
        if len(tx.operations) > 1:
            return False
        operation = tx.operations[0]
        if operation.type != OperationTypes.PAYMENT:
            return False
        if operation.asset != self.kin_asset.code:
            return False
        if source != tx.source or destination != operation.destination or amount != operation.amount:
            return False
        if check_memo and build_memo(app_id, memo) != tx.memo:
            return False

        return True

    def friendbot(self, address):
        """
        Use the friendbot service to create and fund an account
        :param str address: The address to create and fund
        :return: the hash of the friendobt transaction
        :rtype str

        :raises ValueError: if no friendbot service was provided
        :raises ValueError: if the address is invalid
        :raises :class: `KinErrors.AccountExistsError`: if the account already exists
        :raises :class: `KinErrors.FriendbotError`: If the friendbot request failed
        """

        if self.environment.friendbot_url is None:
            raise ValueError("No friendbot service was configured for this client's environments")

        if not is_valid_address(address):
            raise ValueError('invalid address: {}'.format(address))
        if self.get_account_status(address) != AccountStatus.NOT_CREATED:
            raise KinErrors.AccountExistsError(address)

        response = requests.get(self.environment.friendbot_url, params={'addr': address})
        if response.ok:
            return response.json()['hash']
        else:
            raise KinErrors.FriendbotError(response.status_code, response.text)

    def activate_account(self, seed):
        """
        Activate an account.
        :param str seed: The secret seed of the account to activate
        :return: the hash of the transaction
        :rtype: str
        """

        # Check seed
        if not is_valid_secret_key(seed):
            raise ValueError('invalid seed {}'.format(seed))
        # Check the account status
        address = Keypair.address_from_seed(seed)
        status = self.get_account_status(address)

        if status == AccountStatus.NOT_CREATED:
            raise KinErrors.AccountNotFoundError(address)
        if status == AccountStatus.ACTIVATED:
            raise KinErrors.AccountActivatedError(address)

        builder = Builder(self.environment.name, self.horizon, seed)
        builder.append_trust_op(self.kin_asset.issuer, self.kin_asset.code)
        builder.sign()
        reply = builder.submit()

        return reply['hash']

    def monitor_account_payments(self, address, callback_fn):
        """Monitor KIN payment transactions related to the account identified by provided address.
        NOTE: the function starts a background thread.

        :param str address: the address of the account to query.

        :param callback_fn: the function to call on each received payment as `callback_fn(address, tx_data, monitor)`.
        :type: callable[str,:class:`kin.TransactionData`,:class:`kin.SingleMonitor`]

        :return: a monitor instance
        :rtype: :class:`kin.SingleMonitor`

        :raises: ValueError: when no address is given.
        :raises: ValueError: if the address is in the wrong format
        :raises: :class:`KinErrors.AccountNotActivatedError`: if the account given is not activated
        """

        return SingleMonitor(self, address, callback_fn)

    def monitor_accounts_payments(self, addresses, callback_fn):
        """Monitor KIN payment transactions related to multiple accounts
        NOTE: the function starts a background thread.

        :param str addresses: the addresses of the accounts to query.

        :param callback_fn: the function to call on each received payment as `callback_fn(address, tx_data, monitor)`.
        :type: callable[str,:class:`kin.TransactionData`,:class:`kin.MultiMonitor`]

        :return: a monitor instance
        :rtype: :class:`kin.MultiMonitor`

        :raises: ValueError: when no address is given.
        :raises: ValueError: if the addresses are in the wrong format
        :raises: :class:`KinErrors.AccountNotActivatedError`: if the accounts given are not activated
        """

        return MultiMonitor(self, addresses, callback_fn)
