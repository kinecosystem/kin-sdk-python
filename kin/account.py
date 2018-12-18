"""Contains the KinAccount and AccountStatus classes."""

import re
import json

from kin_base.transaction_envelope import TransactionEnvelope
from kin_base.network import NETWORKS

from .blockchain.keypair import Keypair
from .blockchain.horizon import Horizon
from .blockchain.builder import Builder
from .blockchain.channel_manager import ChannelManager, ChannelStatuses
from . import errors as KinErrors
from .transactions import build_memo
from .blockchain.errors import TransactionResultCode, HorizonErrorType, HorizonError
from .config import SDK_USER_AGENT, APP_ID_REGEX
from .blockchain.utils import is_valid_address, is_valid_secret_key

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
        # check that sdk wallet account exists
        if not self._client.does_account_exists(self.keypair.public_address):
            raise KinErrors.AccountNotFoundError(self.keypair.public_address)

        if channel_seeds is not None:
            # Use given channels
            self.channel_seeds = channel_seeds
        else:
            # Use the base account as the only channel
            self.channel_seeds = [seed]

        for channel_seed in self.channel_seeds:
            if not is_valid_secret_key(channel_seed):
                raise KinErrors.StellarSecretInvalidError

        # set connection pool size for channels + monitoring connection + extra
        pool_size = max(1, len(self.channel_seeds)) + 2

        # Set an horizon instance with the new pool_size
        self.horizon = Horizon(self._client.environment.horizon_uri,
                               pool_size=pool_size, user_agent=SDK_USER_AGENT)
        self.channel_manager = ChannelManager(self.channel_seeds)

    def get_public_address(self):
        """Return this KinAccount's public address"""
        return self.keypair.public_address

    def get_balance(self):
        """
        Get the KIN balance of this KinAccount
        :return: the kin balance
        :rtype: float

        :raises: :class:`KinErrors.AccountNotFoundError`: if the account does not exist.
        """
        return self._client.get_account_balance(self.keypair.public_address)

    def get_data(self):
        """
        Gets this KinAccount's data

        :return: account data
        :rtype: :class:`kin.AccountData`

        :raises: :class:`KinErrors.AccountNotFoundError`: if the account does not exist.
        """
        return self._client.get_account_data(self.keypair.public_address)

    def get_status(self, verbose=False):
        """
        Get the config and status of this KinAccount object
        :param bool verbose: Should the channels status be verbose
        :rtype dict
        """
        account_status = {
            'app_id': self.app_id,
            'public_address': self.get_public_address(),
            'balance': self.get_balance(),
            'channels': self.channel_manager.get_status(verbose)
        }
        total_status = {
            'client': self._client.get_config(),
            'account': account_status
        }

        return total_status

    def get_transaction_history(self, amount=10, descending=True, cursor=None, simple=True):
        """
        Get the transaction history for this kin account
        :param int amount: The maximum number of transactions to get
        :param bool descending: The order of the transactions, True will start from the latest one
        :param int cursor: The horizon paging token
        :param bool simple: Should the returned txs be simplified, if True, complicated txs will be ignored
        :return: A list of transactions
        :rtype: list
        """

        return self._client.get_account_tx_history(self.get_public_address(),
                                                   amount=amount,
                                                   descending=descending,
                                                   cursor=cursor,
                                                   simple=simple)

    def get_transaction_builder(self, fee):
        """
        Get a transaction builder using this account
        :param int fee: The fee that will be used for the transaction
        :return: Kin.Builder
        """
        return Builder(self._client.environment.name, self.horizon, fee, self.keypair.secret_seed)

    def create_account(self, address, starting_balance, fee, memo_text=None):
        """Create an account identified by the provided address.

        :param str address: the address of the account to create.

        :param float|str starting_balance: the starting KIN balance of the account.

        :param str memo_text: (optional) a text to put into transaction memo, up to MEMO_CAP chars.

        :param int fee: fee to be deducted for the tx

        :return: the hash of the transaction
        :rtype: str

        :raises: KinErrors.StellarAddressInvalidError: if the provided address has a wrong format.
        :raises: :class:`KinErrors.AccountExistsError`: if the account already exists.
        :raises: :class:`KinErrors.NotValidParamError`: if the memo is longer than MEMO_CAP characters
        :raises: KinErrors.NotValidParamError: if the amount is too precise
        :raises: KinErrors.NotValidParamError: if the fee is not valid
        """
        builder = self.build_create_account(address, starting_balance, fee, memo_text)

        with self.channel_manager.get_channel() as channel:
            builder.set_channel(channel)
            builder.sign(channel)
            # Also sign with the root account if a different channel was used
            if builder.address != self.keypair.public_address:
                builder.sign(self.keypair.secret_seed)
            return self.submit_transaction(builder)

    def send_kin(self, address, amount, fee, memo_text=None):
        """Send KIN to the account identified by the provided address.

        :param str address: the account to send KIN to.

        :param float|str amount: the amount of KIN to send.

        :param str memo_text: (optional) a text to put into transaction memo.

        :param int fee: fee to be deducted

        :return: the hash of the transaction
        :rtype: str

        :raises: KinErrors.StellarAddressInvalidError: if the provided address has a wrong format.
        :raises: ValueError: if the amount is not positive.
        :raises: KinErrors.NotValidParamError: if the amount is too precise
        :raises: :class:`KinErrors.AccountNotFoundError`: if the account does not exist.
        :raises: :class:`KinErrors.LowBalanceError`: if there is not enough KIN to send and pay transaction fee.
        :raises: :class:`KinErrors.NotValidParamError`: if the memo is longer than MEMO_CAP characters
        :raises: KinErrors.NotValidParamError: if the fee is not valid
        """
        builder = self.build_send_kin(address, amount, fee, memo_text)
        with self.channel_manager.get_channel() as channel:
            builder.set_channel(channel)
            builder.sign(channel)
            # Also sign with the root account if a different channel was used
            if builder.address != self.keypair.public_address:
                builder.sign(self.keypair.secret_seed)
            return self.submit_transaction(builder)

    def build_create_account(self, address, starting_balance, fee, memo_text=None):
        """Build a tx that will create an account identified by the provided address.

        :param str address: the address of the account to create.

        :param float|str starting_balance: the starting XLM balance of the account.

        :param str memo_text: (optional) a text to put into transaction memo, up to MEMO_CAP chars.

        :param int fee: fee to be deducted for the tx

        :return: a transaction builder object
        :rtype: :class: `Kin.Builder`

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

    def build_send_kin(self, address, amount, fee, memo_text=None):
        """Build a tx to send KIN to the account identified by the provided address.

        :param str address: the account to send asset to.

        :param float|str amount: the KIN amount to send.

        :param str memo_text: (optional) a text to put into transaction memo.

        :param int fee: fee to be deducted for the tx

        :return: a transaction builder
        :rtype: Kin.Builder

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

    def submit_transaction(self, tx_builder):
        """
        Submit a transaction to the blockchain.
        :param kin.Builder tx_builder: The transaction builder
        :return: The hash of the transaction.
        :rtype: str
        """
        try:
            return tx_builder.submit()['hash']
        # If the channel is out of KIN, top it up and try again
        except HorizonError as e:
            logging.warning('send transaction error with channel {}: {}'.format(tx_builder.address, str(e)))
            if e.type == HorizonErrorType.TRANSACTION_FAILED \
                    and e.extras.result_codes.transaction == TransactionResultCode.INSUFFICIENT_BALANCE:

                self.channel_manager.channel_pool.queue[tx_builder.address] = ChannelStatuses.UNDERFUNDED
                self._top_up(tx_builder.address)
                self.channel_manager.channel_pool.queue[tx_builder.address] = ChannelStatuses.TAKEN

                # Insufficient balance is a "fast-fail", the sequence number doesn't increment
                # so there is no need to build the transaction again
                self.submit_transaction(tx_builder)
            else:
                raise KinErrors.translate_error(e)

    def monitor_payments(self, callback_fn):
        """Monitor KIN payment transactions related to this account
        NOTE: the function starts a background thread.

        :param callback_fn: the function to call on each received payment as `callback_fn(address, tx_data, monitor)`.
        :type: callable[str,:class:`kin.TransactionData`,:class:`kin.SingleMonitor`]

        :return: a monitor instance
        :rtype: :class:`kin.SingleMonitor`
        """
        return self._client.monitor_account_payments(self.keypair.public_address, callback_fn)

    def whitelist_transaction(self, payload):
        """
        Sign on a transaction to whitelist it
        :param str payload: the json received from the client
        :return: a signed transaction encoded as base64
        :rtype str
        """

        # load the object from the json
        if not isinstance(payload, dict):
            payload = json.loads(payload)

        # If the network the client is using is different from the one we are using
        if NETWORKS[self._client.environment.name] != payload['network_id']:
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

    def _top_up(self, address):
        """
        Top up a channel with the base account.
        :param str address: The address to top up
        """
        # In theory, if the sdk runs in threads, and 2 or more channels
        # are out of funds and needed to be topped up at the exact same time
        # there is a chance for a bad_sequence error,
        # however it is virtually impossible that this situation will occur.

        # TODO: let user config the amount of kin to top up
        min_fee = self._client.get_minimum_fee()
        builder = self.get_transaction_builder(min_fee)
        builder.append_payment_op(address, str(min_fee * 1000))
        builder.update_sequence()
        builder.sign()
        builder.submit()
