"""Contains the KinClient class to interact with the blockchain"""

from kin_base import Horizon

from .config import ANON_APP_ID, MAX_RECORDS_PER_REQUEST
from . import errors as KinErrors
from .monitors import single_monitor, multi_monitor
from .transactions import SimplifiedTransaction, RawTransaction
from .account import KinAccount
from .blockchain.horizon_models import AccountData
from .blockchain.utils import is_valid_address, is_valid_transaction_hash
from .version import __version__
from .blockchain.environment import Environment

from typing import List, Optional, Union, AsyncGenerator

import logging

logger = logging.getLogger(__name__)


class KinClient:
    """
    The :class:`kin.KinClient` class is the primary interface to the KIN Python SDK based on Kin Blockchain.
    It maintains a connection context with a Horizon node and hides all the specifics of dealing with Kin REST API.
    """

    def __init__(self, environment: Environment):
        """Create a new instance of the KinClient to query the Kin blockchain.

        :param environment: an environment for the client to point to.

        :return: An instance of the KinClient.
        :rtype: KinErrors.KinClient
        """

        self.environment = environment
        self.network = environment.name

        self.horizon = Horizon(environment.horizon_uri)
        logger.info('Kin Client initialized on network {}, horizon endpoint {}'.
                    format(self.network, self.horizon.horizon_uri))

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.close()

    async def close(self) -> None:
        """Close the connection to the horizon server"""
        await self.horizon.close()

    def kin_account(self, seed: str, channel_secret_keys: Optional[List[str]] = None,
                    app_id: Optional[str] = ANON_APP_ID) -> KinAccount:
        """
        Create a new instance of a KinAccount to perform authenticated operations on the blockchain.

        :param seed: The secret seed of the account that will be used
        :param channel_secret_keys: A list of seeds to be used as channels
        :param app_id: the unique id of your app
        :return: An instance of KinAccount
        """

        # Create a new kin account, using self as the KinClient to be used
        return KinAccount(seed, self, channel_secret_keys, app_id)

    async def get_config(self) -> dict:
        """Get system configuration data and online status.

        :return: a dictionary containing the data
        :rtype: dict
        """
        status = {
            'sdk_version': __version__,
            'environment': self.environment.name,
            'horizon': {
                'uri': str(self.horizon.horizon_uri),
                'online': False,
                'error': None,
            },
            'transport': {
                'pool_size': self.horizon._session.connector.limit,
                'num_retries': self.horizon.num_retries,
                'request_timeout': self.horizon._session._timeout.total,
                'backoff_factor': self.horizon.backoff_factor,
            }
        }

        # now check Horizon connection
        try:
            await self.horizon.metrics()
            status['horizon']['online'] = True
        except Exception as e:
            status['horizon']['error'] = repr(e)

        return status

    async def get_minimum_fee(self) -> int:
        """
        Get the current minimum fee acceptable for a tx

        :return: The minimum fee
        """
        params = {'order': 'desc',
                  'limit': 1}
        return (await self.horizon.ledgers(order='desc', limit=1))['_embedded']['records'][0]['base_fee_in_stroops']

    async def get_account_balance(self, address: str) -> float:
        """
        Get the KIN balance of a given account

        :param address: the public address of the account to query
        :return: the balance of the account

        :raises: StellarAddressInvalidError: if the provided address has the wrong format.
        :raises: KinErrors.AccountNotFoundError if the account does not exist.
        """

        if not is_valid_address(address):
            raise KinErrors.StellarAddressInvalidError('invalid address: {}'.format(address))
        account_data = await self.get_account_data(address)
        for balance in account_data.balances:
            # accounts will always have native asset
            if balance.asset_type == 'native':
                return balance.balance

    async def does_account_exists(self, address: str) -> bool:
        """
        Find out if a given account exists on the blockchain

        :param address: The kin account to query about
        :return: does the account exists on the blockchain

        :raises: KinErrors.StellarAddressInvalidError if the address is not valid.
        """

        if not is_valid_address(address):
            raise KinErrors.StellarAddressInvalidError('invalid address: {}'.format(address))

        try:
            await self.get_account_balance(address)
            return True
        except KinErrors.AccountNotFoundError:
            return False

    async def get_account_data(self, address: str) -> AccountData:
        """Get account data.

        :param address: the public address of the account to query.

        :return: account data

        :raises: StellarAddressInvalidError: if the provided address has a wrong format.
        :raises: :class:`KinErrors.AccountNotFoundError`: if the account does not exist.
        """
        # TODO: might want to simplify the returning data
        if not is_valid_address(address):
            raise KinErrors.StellarAddressInvalidError('invalid address: {}'.format(address))

        try:
            acc = await self.horizon.account(address)
            return AccountData(acc, strict=False)
        except Exception as e:
            err = KinErrors.translate_error(e)
            raise KinErrors.AccountNotFoundError(address) if \
                isinstance(err, KinErrors.ResourceNotFoundError) else err

    async def get_transaction_data(self, tx_hash: str, simple: Optional[bool] = True) -> Union[SimplifiedTransaction, RawTransaction]:
        """Gets transaction data.

        :param tx_hash: transaction hash.
        :param simple: (optional) Should the method return a simplified or raw transaction

        :return: transaction data

        :raises: ValueError: if the provided hash is invalid.
        :raises: :class:`KinErrors.ResourceNotFoundError`: if the transaction does not exist.
        :raises: :class:`KinErrors.CantSimplifyError`: if the tx is too complex to simplify
        """
        # TODO: separate to two methods, get_tx_data & get_raw_tx_data
        if not is_valid_transaction_hash(tx_hash):
            raise ValueError('invalid transaction hash: {}'.format(tx_hash))

        try:
            raw_tx = RawTransaction(await self.horizon.transaction(tx_hash))
        except Exception as e:
            raise KinErrors.translate_error(e)

        if simple:
            return SimplifiedTransaction(raw_tx)
        return raw_tx

    async def get_account_tx_history(self, address: str, amount: Optional[int] = 10, descending: Optional[bool] = True,
                                     cursor: Optional[int] = None,
                                     simple: Optional[bool] = True) -> List[Union[SimplifiedTransaction, RawTransaction]]:
        """
        Get the transaction history for a given account.

        :param address: The public address of the account to query
        :param amount: The maximum number of transactions to get
        :param descending: The order of the transactions, True will start from the latest one
        :param cursor: The horizon paging token
        :param simple: Should the returned txs be simplified, if True, complicated txs will be ignored
        :return: A list of transactions
        """

        if not is_valid_address(address):
            raise KinErrors.StellarAddressInvalidError('invalid address: {}'.format(address))

        if amount <= 0:
            raise ValueError('Limit must be bigger than 0')

        tx_list = []

        requested_amount = amount if amount < MAX_RECORDS_PER_REQUEST else MAX_RECORDS_PER_REQUEST

        horizon_response = await self.horizon.account_transactions(address,
                                                             cursor=cursor, limit=requested_amount,
                                                             order='desc' if descending else 'asc')

        for transaction in horizon_response['_embedded']['records']:
            raw_tx = RawTransaction(transaction)
            if simple:
                try:
                    simple_tx = SimplifiedTransaction(raw_tx)
                    tx_list.append(simple_tx)
                except KinErrors.CantSimplifyError:
                    pass
            else:
                tx_list.append(raw_tx)
            last_cursor = transaction['paging_token']

        remaining_txs = amount - len(tx_list)
        # if we got all the txs that we wanted, or there are no more txs
        # TODO: paging does not work DP-370
        if remaining_txs <= 0 or len(horizon_response['_embedded']['records']) < amount:
            return tx_list
        # If there are anymore transactions, recursively get the next transaction page
        return tx_list.extend(await self.get_account_tx_history(address, remaining_txs, descending, last_cursor, simple))

    async def friendbot(self, address: str) -> str:
        """
        Use the friendbot service to create and fund an account

        :param address: The address to create and fund

        :return: the hash of the friendbot transaction

        :raises ValueError: if no friendbot service was provided
        :raises KinErrors.StellarAddressInvalidError: if the address is invalid
        :raises KinErrors.AccountExistsError if the account already exists
        :raises KinErrors.FriendbotError If the friendbot request failed
        """

        if self.environment.friendbot_url is None:
            raise ValueError("No friendbot service was configured for this client's environments")

        if not is_valid_address(address):
            raise KinErrors.StellarAddressInvalidError('invalid address: {}'.format(address))
        if await self.does_account_exists(address):
            raise KinErrors.AccountExistsError(address)

        response = await self.horizon._session.get(self.environment.friendbot_url, params={'addr': address})
        if response.status == 200:
            return (await response.json(encoding='utf-8'))['hash']
        else:
            raise KinErrors.FriendbotError(response.status, await response.text(encoding='utf-8'))

    async def friendbot_fund(self, address: str, amount: float) -> str:
        """
        Use the friendbot service to create and fund an account

        :param address: The address to create and fund
        :param amount: How much kin to request from the friendbot

        :return: the hash of the friendbot transaction

        :raises ValueError: if no friendbot service was provided
        :raises ValueError: If the amount requested is invalid
        :raises KinErrors.StellarAddressInvalidError: if the address is invalid
        :raises KinErrors.AccountNotFoundError: if the account does not exist
        :raises KinErrors.FriendbotError If the friendbot request failed
        """

        if self.environment.friendbot_url is None:
            raise ValueError("No friendbot service was configured for this client's environments")

        if not 0 < amount <= 10000:
            raise ValueError("Invalid amount for friendbot request")
        if not is_valid_address(address):
            raise KinErrors.StellarAddressInvalidError('invalid address: {}'.format(address))
        if not await self.does_account_exists(address):
            raise KinErrors.AccountNotFoundError(address)

        response = await self.horizon._session.get(self.environment.friendbot_url + '/fund', params={'addr': address, 'amount':amount})
        if response.status == 200:
            return (await response.json(encoding='utf-8'))['hash']
        else:
            raise KinErrors.FriendbotError(response.status, await response.text(encoding='utf-8'))

    def monitor_account_payments(self, address: str, timeout: Optional[float] = None) -> AsyncGenerator[SimplifiedTransaction, None]:
        """Monitor KIN payment transactions related to the account identified by provided address.

        :param str address: the address of the account to query.
        :param timeout: How long to wait for each event

        :raises: ValueError: if the address is in the wrong format
        :raises: asyncio.TimeoutError: If too much time has passed between events (only if "timeout" is set)
        """
        return single_monitor(self, address, timeout=timeout)

    def monitor_accounts_payments(self, addresses: set, timeout: Optional[float] = None) -> AsyncGenerator[SimplifiedTransaction, None]:
        """Monitor KIN payment transactions related to multiple accounts

        :param addresses: the addresses of the accounts to query.
        :param timeout: How long to wait for each event

        :raises: asyncio.TimeoutError: If too much time has passed between events (only if "timeout" is set)
        """
        return multi_monitor(self, addresses, timeout=timeout)
