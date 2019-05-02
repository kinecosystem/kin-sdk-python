"""Contains the KinAccount and AccountStatus classes."""

import re
import json

from kin_base import Builder
from kin_base.network import NETWORKS
from kin_base.transaction_envelope import TransactionEnvelope

from .blockchain.keypair import Keypair
from .blockchain.channel_manager import ChannelManager, ChannelStatuses
from . import errors as KinErrors
from .transactions import build_memo, RawTransaction, SimplifiedTransaction
from .blockchain.errors import TransactionResultCode, HorizonErrorType
from .config import APP_ID_REGEX, KIN_DECIMAL_PRECISION
from .blockchain.utils import is_valid_address, is_valid_secret_key
from .blockchain.horizon_models import AccountData

from typing import List, Optional, Union, AsyncGenerator
import logging

logger = logging.getLogger(__name__)


class KinAccount:
    """Account class to perform authenticated actions on the blockchain"""

    def __init__(self, seed, client, channel_seeds, app_id):
        # Set the internal client
        self._client = client

        # Set the app_id
        self.app_id = app_id

        # Verify the app_id is ok
        if re.match(APP_ID_REGEX, app_id) is None:
            raise ValueError('invalid app id: {}'.format(app_id))

        # Set keypair
        self.keypair = Keypair(seed)

        if channel_seeds is not None:
            # Use given channels
            self.channel_seeds = channel_seeds
            for channel_seed in self.channel_seeds:
                if not is_valid_secret_key(channel_seed):
                    raise KinErrors.StellarSecretInvalidError
        else:
            # Use the base account as the only channel
            self.channel_seeds = [seed]

        self.channel_manager = ChannelManager(self.channel_seeds)

    def get_public_address(self):
        """Return this KinAccount's public address"""
        return self.keypair.public_address

    async def get_balance(self) -> float:
        """
        Get the KIN balance of this KinAccount

        :return: the kin balance

        :raises: KinErrors.AccountNotFoundError if the account does not exist.
        """
        return await self._client.get_account_balance(self.keypair.public_address)

    async def get_data(self) -> AccountData:
        """
        Gets this KinAccount's data

        :return: account data

        :raises: KinErrors.AccountNotFoundError if the account does not exist.
        """
        return await self._client.get_account_data(self.keypair.public_address)

    async def get_status(self, verbose: Optional[bool] = False) -> dict:
        """
        Get the config and status of this KinAccount object

        :param verbose: Should the channels status be verbose
        :return: The config and status of this KinAccount object
        :rtype dict
        """
        account_status = {
            'app_id': self.app_id,
            'public_address': self.get_public_address(),
            'balance': await self.get_balance(),
            'channels': self.channel_manager.get_status(verbose)
        }
        total_status = {
            'client': await self._client.get_config(),
            'account': account_status
        }

        return total_status

    async def get_transaction_history(self, amount: Optional[int] = 10, descending: Optional[bool] = True,
                                      cursor: Optional[int] = None,
                                      simple: Optional[bool] = True) -> List[Union[SimplifiedTransaction, RawTransaction]]:
        """
        Get the transaction history for this kin account

        :param amount: The maximum number of transactions to get
        :param descending: The order of the transactions, True will start from the latest one
        :param cursor: The horizon paging token
        :param simple: Should the returned txs be simplified, if True, complicated txs will be ignored
        :return: A list of transactions
        """

        return await self._client.get_account_tx_history(self.get_public_address(),
                                                         amount=amount,
                                                         descending=descending,
                                                         cursor=cursor,
                                                         simple=simple)

    def get_transaction_builder(self, fee: int) -> Builder:
        """
        Get a transaction builder using this account

        :param fee: The fee that will be used for the transaction
        """
        return Builder(horizon=self._client.horizon,
                       network_name=self._client.environment.name,
                       fee=fee,
                       secret=self.keypair.secret_seed)

    async def create_account(self, address: str, starting_balance: Union[float, str], fee: int,
                             memo_text: Optional[str] = None) -> str:
        """Create an account identified by the provided address.

        :param address: the address of the account to create.
        :param starting_balance: the starting KIN balance of the account.
        :param memo_text: (optional) a text to put into transaction memo, up to MEMO_CAP chars.
        :param fee: fee to be deducted for the tx

        :return: the hash of the transaction

        :raises: KinErrors.StellarAddressInvalidError: if the provided address has a wrong format.
        :raises: KinErrors.AccountExistsError if the account already exists.
        :raises: KinErrors.NotValidParamError if the memo is longer than MEMO_CAP characters
        :raises: KinErrors.NotValidParamError: if the amount is too precise
        :raises: KinErrors.NotValidParamError: if the fee is not valid
        """
        builder = self.build_create_account(address, starting_balance, fee, memo_text)

        async with self.channel_manager.get_channel() as channel:
            await builder.set_channel(channel)
            builder.sign(channel)
            # Also sign with the root account if a different channel was used
            if builder.address != self.keypair.public_address:
                builder.sign(self.keypair.secret_seed)
            return await self.submit_transaction(builder)

    async def send_kin(self, address: str, amount: Union[float, str], fee: int,
                       memo_text: Optional[str] = None) -> str:
        """Send KIN to the account identified by the provided address.

        :param address: the account to send KIN to.
        :param amount: the amount of KIN to send.
        :param memo_text: (optional) a text to put into transaction memo.
        :param fee: fee to be deducted

        :return: the hash of the transaction

        :raises: KinErrors.StellarAddressInvalidError: if the provided address has a wrong format.
        :raises: ValueError: if the amount is not positive.
        :raises: KinErrors.NotValidParamError: if the amount is too precise
        :raises: KinErrors.AccountNotFoundError if the account does not exist.
        :raises: KinErrors.LowBalanceError if there is not enough KIN to send and pay transaction fee.
        :raises: KinErrors.NotValidParamError if the memo is longer than MEMO_CAP characters
        :raises: KinErrors.NotValidParamError: if the fee is not valid
        """
        builder = self.build_send_kin(address, amount, fee, memo_text)
        async with self.channel_manager.get_channel() as channel:
            await builder.set_channel(channel)
            builder.sign(channel)
            # Also sign with the root account if a different channel was used
            if builder.address != self.keypair.public_address:
                builder.sign(self.keypair.secret_seed)
            return await self.submit_transaction(builder)

    def build_create_account(self, address: str, starting_balance: Union[float, str], fee: int,
                          memo_text: Optional[str] = None) -> Builder:
        """Build a tx that will create an account identified by the provided address.
        
        :param address: the address of the account to create.
        :param starting_balance: the starting XLM balance of the account.
        :param memo_text: (optional) a text to put into transaction memo, up to MEMO_CAP chars.
        :param fee: fee to be deducted for the tx

        :return: a transaction builder object

        :raises: KinErrors.StellarAddressInvalidError: if the supplied address has a wrong format.
        """
        if not is_valid_address(address):
            raise KinErrors.StellarAddressInvalidError('invalid address: {}'.format(address))

        if float(starting_balance) < 0:
            raise ValueError('Starting balance : {} cant be negative'.format(starting_balance))

        # Build the transaction.
        builder = self.get_transaction_builder(fee)
        builder.add_text_memo(build_memo(self.app_id, memo_text))
        builder.append_create_account_op(address, str(starting_balance), source=self.keypair.public_address)
        return builder

    def build_send_kin(self, address: str, amount: Union[float, str], fee: int,
                       memo_text: Optional[str] = None) -> Builder:
        """Build a tx to send KIN to the account identified by the provided address.

        :param address: the account to send asset to.
        :param amount: the KIN amount to send.
        :param memo_text: (optional) a text to put into transaction memo.
        :param fee: fee to be deducted for the tx

        :return: a transaction builder

        :raises: KinErrors.StellarAddressInvalidError: if the provided address has a wrong format.
        :raises: ValueError: if the amount is not positive.
        """

        if not is_valid_address(address):
            raise KinErrors.StellarAddressInvalidError('invalid address: {}'.format(address))

        if float(amount) <= 0:
            raise ValueError('Amount : {} must be positive'.format(amount))

        builder = self.get_transaction_builder(fee)
        builder.add_text_memo(build_memo(self.app_id, memo_text))
        builder.append_payment_op(address, str(amount), source=self.keypair.public_address)
        return builder

    async def submit_transaction(self, tx_builder: Builder) -> str:
        """
        Submit a transaction to the blockchain.

        :param kin.Builder tx_builder: The transaction builder

        :return: The hash of the transaction.
        :rtype: str
        """
        try:
            return (await tx_builder.submit())['hash']
        # If the channel is out of KIN, top it up and try again
        except KinErrors.HorizonError as e:
            logger.warning('send transaction error with channel {}: {}'.format(tx_builder.address, str(e)))
            if e.type == HorizonErrorType.TRANSACTION_FAILED \
                    and e.extras['result_codes']['transaction'] == TransactionResultCode.INSUFFICIENT_BALANCE:

                self.channel_manager.channel_pool._queue[tx_builder.address] = ChannelStatuses.UNDERFUNDED
                await self._top_up(tx_builder.address)
                self.channel_manager.channel_pool._queue[tx_builder.address] = ChannelStatuses.TAKEN

                # Insufficient balance is a "fast-fail", the sequence number doesn't increment
                # so there is no need to build the transaction again
                await self.submit_transaction(tx_builder)
            else:
                raise KinErrors.translate_error(e)

    def monitor_payments(self, timeout: Optional[float] = None) -> AsyncGenerator[SimplifiedTransaction, None]:
        """Monitor KIN payment transactions related to this account

        :param timeout: How long to wait for each event

        :raises: ValueError: if the address is in the wrong format
        :raises: asyncio.TimeoutError: If too much time has passed between events (only if "timeout" is set)
        """
        return self._client.monitor_account_payments(self.keypair.public_address, timeout)

    def whitelist_transaction(self, payload: Union[str, dict]) -> str:
        """
        Sign on a transaction to whitelist it

        :param payload: the json received from the client
        :return: a signed transaction encoded as base64
        """

        # load the object from the json
        if not isinstance(payload, dict):
            payload = json.loads(payload)

        # If the network the client is using is different from the one we are using
        if self._client.environment.passphrase != payload['network_id']:
            raise KinErrors.WrongNetworkError()

        # The android stellar sdk spells 'tx-envelope' as 'envelop'
        payload_envelope = payload.get('envelop',payload.get('envelope'))
        # Decode the transaction, from_xdr actually takes a base64 encoded xdr
        envelope = TransactionEnvelope.from_xdr(payload_envelope)

        # Add the network_id hash to the envelope
        envelope.network_id = self._client.environment.passphrase_hash

        # Get the transaction hash (to sign it)
        tx_hash = envelope.hash_meta()

        # Sign using the hash
        signature = self.keypair.sign(tx_hash)

        # Add the signature to the envelope
        envelope.signatures.append(signature)

        # Pack the signed envelop to xdr the return it encoded as base64
        # xdr() returns a bytestring that needs to be decoded
        return envelope.xdr().decode()

    # Internal methods

    async def _top_up(self, address: str) -> None:
        """
        Top up a channel with the base account.

        :param address: The address to top up
        """

        # TODO: let user config the amount of kin to top up
        min_fee = await self._client.get_minimum_fee()
        builder = self.get_transaction_builder(min_fee)
        builder.append_payment_op(address, str((min_fee / KIN_DECIMAL_PRECISION) * 1000))  # Enough for 1K txs
        await builder.update_sequence()
        builder.sign()
        await builder.submit()
