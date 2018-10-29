"""Contains the KinAccount and AccountStatus classes."""

import sys
import re
from functools import partial

from enum import Enum
from stellar_base.asset import Asset

from .blockchain.keypair import Keypair
from .blockchain.horizon import Horizon
from .blockchain.builder import Builder
from .blockchain.channel_manager import ChannelManager
from . import errors as KinErrors
from .transactions import Transaction, build_memo
from .blockchain.errors import TransactionResultCode, HorizonErrorType, HorizonError
from .config import MIN_ACCOUNT_BALANCE, SDK_USER_AGENT, DEFAULT_FEE, MEMO_CAP, MEMO_TEMPLATE, APP_ID_REGEX
from .blockchain.utils import is_valid_secret_key, is_valid_address

import logging

logger = logging.getLogger(__name__)


class KinAccount:
    """Account class to perform authenticated actions on the blockchain"""

    def __init__(self, seed, client, channels, channel_secret_keys, create_channels, app_id):
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
        # check that sdk wallet account exists and is activated, issuer should continue without activation
        if self._client.get_account_status(self.keypair.public_address) != AccountStatus.ACTIVATED and \
                        self.keypair.public_address != self._client.kin_asset.issuer:
            raise KinErrors.AccountNotActivatedError(self.keypair.public_address)

        if channels is not None and channel_secret_keys is not None:
            raise ValueError("Account cannot be initialized with both 'channels'"
                             " and 'channel_secret_keys' parameters")

        if channel_secret_keys is not None:
            # Use given channels
            self.channel_secret_keys = channel_secret_keys

        elif channels is not None:
            # Generate the channels for the user
            self.channel_secret_keys = [Keypair.generate_hd_seed(seed, str(channel)) for channel in range(channels)]
        else:
            # Use the base account as the only channel
            self.channel_secret_keys = [seed]

        if create_channels:
            if channels is None:
                raise ValueError("create_channels can only be used with the channels parameter")

            # Create the channels using the base account
            if self.channel_secret_keys == [seed]:
                raise ValueError('There are no channels to create')
            base_account = self._client.kin_account(seed,app_id=app_id)

            # Verify that there is enough XLM to create the channels
            # Balance should be at least (Number of channels + yourself) * (Minimum account balance + fees)
            if (len(self.channel_secret_keys) + 1) * (MIN_ACCOUNT_BALANCE + DEFAULT_FEE) > \
                    base_account.get_balances()['XLM']:
                raise KinErrors.LowBalanceError('The base account does not have enough XLM to create the channels')

            # Create the channels, pass if the channel already exists
            for channel in self.channel_secret_keys:
                try:
                    # TODO: might want to make it a 1 multi operation tx
                    base_account.create_account(Keypair.address_from_seed(channel), activate=False)
                except KinErrors.AccountExistsError:
                    pass

        for channel_key in self.channel_secret_keys:
            # Verify channel seed
            if not is_valid_secret_key(channel_key):
                raise ValueError('invalid channel key: {}'.format(channel_key))
            # Check that channel accounts exists (they do not have to be activated).
            channel_address = Keypair.address_from_seed(channel_key)
            if self._client.get_account_data(channel_address) == AccountStatus.NOT_CREATED:
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

    def get_balances(self):
        """
        Get the KIN and XLM balance of this KinAccount
        :return: a dictionary containing the balances

        :raises: :class:`KinErrors.AccountNotFoundError`: if the account does not exist.
        """
        return self._client.get_account_balances(self.keypair.public_address)

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
                                                   amount=10,
                                                   descending=True,
                                                   cursor=None,
                                                   simple=True)

    def create_account(self, address, starting_balance=MIN_ACCOUNT_BALANCE, memo_text=None, activate=True):
        """Create an account identified by the provided address.

        :param str address: the address of the account to create.

        :param number starting_balance: (optional) the starting XLM balance of the account.
        If not provided, a default MIN_ACCOUNT_BALANCE will be used.

        # TODO: might want to limit this if we use tx_coloring
        :param str memo_text: (optional) a text to put into transaction memo, up to MEMO_CAP chars.
        :param bool activate: (optional) should the created account be activated
        :return: the hash of the transaction
        :rtype: str

        :raises: ValueError: if the supplied address has a wrong format.
        :raises: :class:`KinErrors.AccountExistsError`: if the account already exists.
        :raises: :class:`KinErrors.MemoTooLongError`: if the memo is longer than MEMO_CAP characters
        """

        tx = self.build_create_account(address,
                                       starting_balance=starting_balance,
                                       memo_text=memo_text, activate=activate)
        return self.submit_transaction(tx)

    def send_xlm(self, address, amount, memo_text=None):
        """Send XLM to the account identified by the provided address.

        :param str address: the account to send XLM to.

        :param number amount: the number of XLM to send.

        # TODO: might want to limit this if we do tx coloring
        :param str memo_text: (optional) a text to put into transaction memo.

        :return: the hash of the transaction
        :rtype: str

        :raises: ValueError: if the provided address has a wrong format.
        :raises: ValueError: if the amount is not positive.
        :raises: :class:`KinErrors.AccountNotFoundError`: if the account does not exist.
        :raises: :class:`KinErrors.LowBalanceError`: if there is not enough XLM to send and pay transaction fee.
        :raises: :class:`KinErrors.MemoTooLongError`: if the memo is longer than MEMO_CAP characters
        """
        tx = self._build_send_asset(Asset.native(), address, amount, memo_text)
        return self.submit_transaction(tx)

    def send_kin(self, address, amount, memo_text=None):
        """Send KIN to the account identified by the provided address.

        :param str address: the account to send KIN to.

        :param number amount: the amount of KIN to send.

        # TODO: might want to limit this if we do tx coloring
        :param str memo_text: (optional) a text to put into transaction memo.

        :return: the hash of the transaction
        :rtype: str

        :raises: ValueError: if the provided address has a wrong format.
        :raises: ValueError: if the amount is not positive.
        :raises: :class:`KinErrors.AccountNotFoundError`: if the account does not exist.
        :raises: :class:`KinErrors.AccountNotActivatedError`: if the account is not activated.
        :raises: :class:`KinErrors.LowBalanceError`: if there is not enough KIN and XLM to send and pay transaction fee.
        :raises: :class:`KinErrors.MemoTooLongError`: if the memo is longer than MEMO_CAP characters
        """
        tx = self._build_send_asset(self._client.kin_asset, address, amount, memo_text)
        return self.submit_transaction(tx)

    def build_create_account(self, address, starting_balance=MIN_ACCOUNT_BALANCE, memo_text=None,
                             activate=True):
        """Build a tx that will create an account identified by the provided address.

        :param str address: the address of the account to create.

        :param number starting_balance: (optional) the starting XLM balance of the account.
        If not provided, a default MIN_ACCOUNT_BALANCE will be used.

        # TODO: might want to limit this if we use tx_coloring
        :param str memo_text: (optional) a text to put into transaction memo, up to MEMO_CAP chars.
        :param bool activate: (optional) should the created account be activated
        :return: a transaction object
        :rtype: :class: `Kin.Transaction`

        :raises: ValueError: if the supplied address has a wrong format.
        :raises: :class:`KinErrors.MemoTooLongError`: if the memo is longer than MEMO_CAP characters
        """
        if not is_valid_address(address):
            raise ValueError('invalid address: {}'.format(address))

        # Build the transaction and send it.

        pretrusted_asset = self._client.kin_asset if activate else None

        builder = self.channel_manager.build_transaction(lambda builder:
                                                         partial(builder.append_create_account_op, address,
                                                                 starting_balance, kin_asset=pretrusted_asset),
                                                         memo_text=build_memo(self.app_id, memo_text))
        return Transaction(builder, self.channel_manager)

    def build_send_xlm(self, address, amount, memo_text=None):
        """Send XLM to the account identified by the provided address.

        :param str address: the account to send XLM to.

        :param number amount: the number of XLM to send.

        # TODO: might want to limit this if we do tx coloring
        :param str memo_text: (optional) a text to put into transaction memo.

        :return: a transaction object
        :rtype: :class: `Kin.Transaction`

        :raises: ValueError: if the provided address has a wrong format.
        :raises: ValueError: if the amount is not positive.
        """
        return self._build_send_asset(Asset.native(), address, amount, memo_text)

    def build_send_kin(self, address, amount, memo_text=None):
        """Send KIN to the account identified by the provided address.

         :param str address: the account to send KIN to.

         :param number amount: the amount of KIN to send.

         # TODO: might want to limit this if we do tx coloring
         :param str memo_text: (optional) a text to put into transaction memo.

        :return: a transaction object
        :rtype: :class: `Kin.Transaction`

         :raises: ValueError: if the provided address has a wrong format.
         :raises: ValueError: if the amount is not positive.
         """
        return self._build_send_asset(self._client.kin_asset, address, amount, memo_text)

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
        # If the channel is out of XLM, top it up and try again
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

    # Internal methods

    def _build_send_asset(self, asset, address, amount, memo_text=None):
        """Build a tx to send asset to the account identified by the provided address.

        :param str address: the account to send asset to.

        :param asset: asset to send
        :type: :class:`stellar_base.asset.Asset`

        :param number amount: the asset amount to send.

        :param str memo_text: (optional) a text to put into transaction memo.

        :return: a transaction object
        :rtype: :class: `Kin.Transaction`

        :raises: ValueError: if the provided address has a wrong format.
        :raises: ValueError: if the amount is not positive.
        :raises: ValueError: if the amount is too precise
        """

        if not is_valid_address(address):
            raise ValueError('invalid address: {}'.format(address))

        if amount <= 0:
            raise ValueError('amount must be positive')

        if amount * 1e7 % 1 != 0:
            raise ValueError('Number of digits after the decimal point in the amount exceeded the limit(7).')

        builder = self.channel_manager.build_transaction(lambda builder:
                                                         partial(builder.append_payment_op, address, amount,
                                                                 asset_code=asset.code, asset_issuer=asset.issuer),
                                                         memo_text=build_memo(self.app_id, memo_text))
        return Transaction(builder, self.channel_manager)

    def _top_up(self, address):
        """
        Top up a channel with the base account.
        :param str address: The address to top up
        """
        # In theory, if the sdk runs in threads, and 2 or more channels
        # are out of funds and needed to be topped up at the exact same time
        # there is a chance for a bad_sequence error,
        # however it is virtually impossible that this situation will occur.

        builder = Builder(self._client.environment.name, self._client.horizon, self.keypair.secret_seed)
        builder.append_payment_op(address, 1)
        builder.sign()
        builder.submit()


class AccountStatus(Enum):
    # Account statuses enum
    NOT_CREATED = 1
    NOT_ACTIVATED = 2
    ACTIVATED = 3
