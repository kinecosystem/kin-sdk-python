"""Contains the KinAccount and AccountStatus classes."""

import re
from functools import partial
import json

from kin_base.transaction_envelope import TransactionEnvelope
from kin_base.network import NETWORKS

from .blockchain.keypair import Keypair
from .blockchain.horizon import Horizon
from .blockchain.builder import Builder
from .blockchain.channel_manager import ChannelManager
from . import errors as KinErrors
from .transactions import Transaction, build_memo
from .blockchain.errors import TransactionResultCode, HorizonErrorType, HorizonError
from .config import SDK_USER_AGENT, APP_ID_REGEX
from .blockchain.utils import is_valid_secret_key, is_valid_address

import logging

logger = logging.getLogger(__name__)


class KinAccount:
    """Account class to perform authenticated actions on the blockchain"""

    def __init__(self, seed, client, channel_secret_keys, app_id):
        # Set the internal sdk
        self._client = client

        # Set the app_id
        self.app_id = app_id

        # Verify the app_id is ok
        if re.match(APP_ID_REGEX, app_id) is None:
            raise ValueError('invalid app id: {}'.format(app_id))

        # Verify seed
        if not is_valid_secret_key(seed):
            raise ValueError('invalid secret key: {}'.format(seed))

        # Set keypair
        self.keypair = Keypair(seed)
        # check that sdk wallet account exists
        if not self._client.does_account_exists(self.keypair.public_address):
            raise KinErrors.AccountNotFoundError(self.keypair.public_address)

        if channel_secret_keys is not None:
            # Use given channels
            self.channel_secret_keys = channel_secret_keys
        else:
            # Use the base account as the only channel
            self.channel_secret_keys = [seed]

        for channel_key in self.channel_secret_keys:
            # Verify channel seed
            if not is_valid_secret_key(channel_key):
                raise KinErrors.StellarSecretInvalidError('invalid channel key: {}'.format(channel_key))
            # Check that channel accounts exists.
            channel_address = Keypair.address_from_seed(channel_key)
            if not self._client.does_account_exists(channel_address):
                raise KinErrors.AccountNotFoundError(channel_address)

        # set connection pool size for channels + monitoring connection + extra
        pool_size = max(1, len(self.channel_secret_keys)) + 2

        # Set an horizon instance with the new pool_size
        self.horizon = Horizon(self._client.environment.horizon_uri,
                               pool_size=pool_size, user_agent=SDK_USER_AGENT)
        self.channel_manager = ChannelManager(seed, self.channel_secret_keys,
                                              self._client.environment.name, self.horizon)

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

    def create_account(self, address, starting_balance, fee, memo_text=None):
        """Create an account identified by the provided address.

        :param str address: the address of the account to create.

        :param number starting_balance: the starting KIN balance of the account.

        :param str memo_text: (optional) a text to put into transaction memo, up to MEMO_CAP chars.

        :param float fee: fee to be deducted for the tx

        :return: the hash of the transaction
        :rtype: str

        :raises: ValueError: if the supplied address has a wrong format.
        :raises: :class:`KinErrors.AccountExistsError`: if the account already exists.
        :raises: :class:`KinErrors.NotValidParamError`: if the memo is longer than MEMO_CAP characters
        :raises: KinErrors.NotValidParamError: if the amount is too precise
        :raises: KinErrors.NotValidParamError: if the fee is not an too precise
        """
        tx = self.build_create_account(address,
                                       starting_balance=starting_balance,
                                       fee=fee,
                                       memo_text=memo_text)
        return self.submit_transaction(tx)

    def send_kin(self, address, amount, fee, memo_text=None):
        """Send KIN to the account identified by the provided address.

        :param str address: the account to send KIN to.

        :param number amount: the amount of KIN to send.

        :param str memo_text: (optional) a text to put into transaction memo.

        :param float fee: fee to be deducted

        :return: the hash of the transaction
        :rtype: str

        :raises: ValueError: if the provided address has a wrong format.
        :raises: ValueError: if the amount is not positive.
        :raises: KinErrors.NotValidParamError: if the amount is too precise
        :raises: :class:`KinErrors.AccountNotFoundError`: if the account does not exist.
        :raises: :class:`KinErrors.AccountNotActivatedError`: if the account is not activated.
        :raises: :class:`KinErrors.LowBalanceError`: if there is not enough KIN and XLM to send and pay transaction fee.
        :raises: :class:`KinErrors.NotValidParamError`: if the memo is longer than MEMO_CAP characters
        :raises: KinErrors.NotValidParamError: if the fee is not an too precise
        """
        tx = self.build_send_kin(address, amount, fee, memo_text)
        return self.submit_transaction(tx)

    def build_create_account(self, address, starting_balance, fee, memo_text=None):
        """Build a tx that will create an account identified by the provided address.

        :param str address: the address of the account to create.

        :param number starting_balance: the starting XLM balance of the account.

        :param str memo_text: (optional) a text to put into transaction memo, up to MEMO_CAP chars.

        :param float fee: fee to be deducted for the tx

        :return: a transaction object
        :rtype: :class: `Kin.Transaction`

        :raises: ValueError: if the supplied address has a wrong format.
        :raises: :class:`KinErrors.NotValidParamError`: if the memo is longer than MEMO_CAP characters
        :raises: KinErrors.NotValidParamError: if the amount is too precise
        :raises: KinErrors.NotValidParamError: if the fee is not an too precise
        """
        if not is_valid_address(address):
            raise KinErrors.StellarAddressInvalidError('invalid address: {}'.format(address))

        if float(starting_balance) < 0:
            raise ValueError('Starting balance : {} cant be negative'.format(starting_balance))

        # Build the transaction and send it.

        builder = self.channel_manager.build_transaction(lambda builder:
                                                         partial(builder.append_create_account_op, address,
                                                                 str(starting_balance)),
                                                         fee,
                                                         memo_text=build_memo(self.app_id, memo_text))
        return Transaction(builder, self.channel_manager)

    def build_send_kin(self, address, amount, fee, memo_text=None):
        """Build a tx to send KIN to the account identified by the provided address.

        :param str address: the account to send asset to.

        :param number amount: the asset amount to send.

        :param str memo_text: (optional) a text to put into transaction memo.

        :param float fee: fee to be deducted for the tx

        :return: a transaction object
        :rtype: :class: `Kin.Transaction`

        :raises: ValueError: if the provided address has a wrong format.
        :raises: ValueError: if the amount is not positive.
        :raises: KinErrors.NotValidParamError: if the amount is too precise
        :raises: KinErrors.NotValidParamError: if the fee is not an too precise
        """

        if not is_valid_address(address):
            raise KinErrors.StellarAddressInvalidError('invalid address: {}'.format(address))

        if float(amount) <= 0:
            raise ValueError('Amount : {} must be positive'.format(amount))

        builder = self.channel_manager.build_transaction(lambda builder:
                                                         partial(builder.append_payment_op, address, str(amount)),
                                                         fee,
                                                         memo_text=build_memo(self.app_id, memo_text))
        return Transaction(builder, self.channel_manager)

    def submit_transaction(self, tx, is_re_submitting=False):
        """
        Submit a transaction to the blockchain.
        :param :class: `kin.Transaction` tx: The transaction object to send
        :param boolean is_re_submitting: is this a re-submission
        :return: The hash of the transaction.
        :rtype: str
        """
        try:
            return tx.builder.submit()['hash']
        # If the channel is out of KIN, top it up and try again
        except HorizonError as e:
            logging.warning('send transaction error with channel {}: {}'.format(tx.builder.address, str(e)))
            if e.type == HorizonErrorType.TRANSACTION_FAILED \
                    and e.extras.result_codes.transaction == TransactionResultCode.INSUFFICIENT_BALANCE:
                tx.channel_manager.low_balance_builders.append(tx.builder)
                self._top_up(tx.builder.address)
                tx.channel_manager.low_balance_builders.remove(tx.builder)

                # Insufficient balance is a "fast-fail", the sequence number doesn't increment
                # so there is no need to build the transaction again
                self.submit_transaction(tx, is_re_submitting=True)
            else:
                raise KinErrors.translate_error(e)
        finally:
            if not is_re_submitting:
                tx.release()

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

        # Add the network_id hash to the envelop
        envelope.network_id = self._client.environment.passphrase_hash

        # Get the transaction hash (to sign it)
        tx_hash = envelope.hash_meta()

        # Sign using the hash
        signature = self.keypair.sign(tx_hash)

        # Add the signature to the envelop
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
        builder = Builder(self._client.environment.name, self._client.horizon,
                          self._client.get_minimum_fee(), self.keypair.secret_seed)
        builder.append_payment_op(address, str(self._client.get_minimum_fee() * 1000))
        builder.sign()
        builder.submit()
