# -*- coding: utf-8 -*

# Copyright (C) 2018 Kin Foundation

from decimal import Decimal, getcontext
from functools import partial

from stellar_base.asset import Asset
from stellar_base.keypair import Keypair

from .channel_manager import ChannelManager
from .exceptions import (
    SdkConfigurationError,
    SdkNotConfiguredError,
    SdkHorizonError,
)
from .horizon import Horizon
from .models import AccountData, TransactionData
from .utils import validate_address, validate_seed, check_horizon_reply

import logging
logger = logging.getLogger(__name__)

getcontext().prec = 7  # IMPORTANT: XLM decimal precision

KIN_ISSUER = 'GDVDKQFP665JAO7A2LSHNLQIUNYNAAIGJ6FYJVMG4DT3YJQQJSRBLQDG'  # TODO: real address
KIN_ASSET = Asset('KIN', KIN_ISSUER)

# https://www.stellar.org/developers/guides/concepts/fees.html
BASE_RESERVE = 0.5  # in XLM
MIN_ACCOUNT_BALANCE = (2 + 1) * BASE_RESERVE  # 1 additional trustline op


class SDK(object):
    """
    The :class:`~kin.SDK` class is the primary interface to the KIN Python SDK based on Stellar Blockchain.
    It maintains a connection context with a Horizon node and hides all the specifics of dealing with Stellar REST API.
    """

    def __init__(self, base_seed='', horizon_endpoint_uri='', network='PUBLIC', channel_seeds=[]):
        """Create a new instance of the KIN SDK for Stellar.

        If seed is not provided, the SDK can still be used in "anonymous" mode with only the following
        functions available:
            - get_address_lumen_balance
            - get_address_kin_balance
            - check_kin_trusted
            - check_account_exists
            - get_account_data
            - get_transaction_data
            - monitor_address_transactions

        :param str seed: a seed to initialize the sdk wallet account with. If not provided, the wallet will not be
            initialized and methods needing the wallet will raise exception.

        :param str horizon_endpoint_uri: a Horizon endpoint. If not provided, a default endpoint will be used,
            either a testnet or pubnet, depending on the `network` parameter.

        :param str network: either PUBLIC or TESTNET, will set the Horizon endpoint in the absence of
            `horizon_endpoint_uri`.

        :param list channel_seeds: a list of channels to sign transactions with. More channels means less blocking
            on transactions and better response time.

        :return: An instance of the SDK.
        :rtype: :class:`~kin.SDK`

        :raises: :class:`~kin.SdkConfigurationError` if some of the configuration parameters are invalid.
        """

        self.network = network or 'PUBLIC'

        pool_size = max(1, len(channel_seeds)) + 2  # for monitoring connection + extra
        if horizon_endpoint_uri:
            self.horizon = Horizon(horizon_uri=horizon_endpoint_uri, pool_size=pool_size)
        else:
            from stellar_base.horizon import HORIZON_LIVE, HORIZON_TEST
            if self.network == 'TESTNET':
                self.horizon = Horizon(horizon_uri=HORIZON_TEST, pool_size=pool_size)
            else:
                self.horizon = Horizon(horizon_uri=HORIZON_LIVE, pool_size=pool_size)

        # check Horizon connection
        try:
            self.horizon.query('')
        except Exception as e:
            raise SdkConfigurationError('cannot connect to horizon')

        # init sdk account base_keypair if a base_seed is supplied
        self.base_keypair = None
        if base_seed:
            try:
                validate_seed(base_seed)
            except ValueError:
                raise SdkConfigurationError('invalid base seed: {}'.format(base_seed))
            self.base_keypair = Keypair.from_seed(base_seed)

            # check channel seeds
            if channel_seeds:
                for channel_seed in channel_seeds:
                    try:
                        validate_seed(channel_seed)
                    except ValueError:
                        raise SdkConfigurationError('invalid channel seed: {}'.format(channel_seed))
            else:
                channel_seeds = [base_seed]

            # init channel manager
            self.channel_manager = ChannelManager(base_seed, channel_seeds, self.network, self.horizon)

    def get_address(self):
        """Get the address of the SDK wallet account.
        The wallet is configured by a seed supplied during SDK initialization.

        :return: public address of the wallet.
        :rtype: str

        :raises: :class:`~kin.SdkConfigurationError`: if the SDK wallet is not configured.
        """
        if not self.base_keypair:
            raise SdkNotConfiguredError('address not configured')
        return self.base_keypair.address().decode()

    def get_lumen_balance(self):
        """Get lumen balance of the SDK wallet.
        The wallet is configured by a seed supplied during SDK initialization.

        :return: : the balance in lumens.
        :rtype: Decimal

        :raises: :class:`~kin.SdkConfigurationError`: if the SDK wallet is not configured.
        """
        return self.get_address_lumen_balance(self.get_address())

    def get_kin_balance(self):
        """Get KIN balance of the SDK wallet.
        The wallet is configured by a seed supplied during SDK initialization.

        :return: : the balance in KIN.
        :rtype: Decimal

        :raises: :class:`~kin.SdkConfigurationError`: if the SDK wallet is not configured.
        """
        return self.get_address_kin_balance(self.get_address())

    def get_address_lumen_balance(self, address):
        """Get lumen balance of the account identified by the provided address.

        :param: str address: the address of the account to query.

        :return: the lumen balance of the account.
        :rtype: Decimal

        :raises: ValueError: if the supplied address has a wrong format.
        """
        return self.get_address_asset_balance(address, Asset.native())

    def get_address_kin_balance(self, address):
        """Get KIN balance of the account identified by the provided address.

        :param: str address: the address of the account to query.

        :return: : the balance in KIN of the account.
        :rtype: Decimal

        :raises: ValueError: if the supplied address has a wrong format.
        """
        return self.get_address_asset_balance(address, KIN_ASSET)

    def get_address_asset_balance(self, address, asset):
        """Get asset balance of the account identified by the provided address.

        :param: str address: the address of the account to query.

        :return: : the balance in asset units of the account.
        :rtype: Decimal

        :raises: ValueError: if the supplied address has a wrong format.
        """
        if not asset.is_native():
            try:
                validate_address(asset.issuer)
            except ValueError:
                raise ValueError('asset issuer invalid')

        acc_data = self.get_account_data(address)
        for balance in acc_data.balances:
            if (balance.asset_type == 'native' and asset.code == 'XLM') \
                    or (balance.asset_code == asset.code and balance.asset_issuer == asset.issuer):
                return balance.balance
        return 0

    def create_account(self, address, starting_balance=MIN_ACCOUNT_BALANCE, memo_text=None):
        """Create a stellar account identified by the provided address.

        :param str address: the address of the account to create.

        :param number starting_balance: the starting balance of the account. If not provided, a default
            MIN_ACCOUNT_BALANCE will be used.

        :param str memo_text: a text to put into transaction memo.

        :return: transaction hash
        :rtype: str

        :raises: :class:`~kin.SdkConfigurationError` if the SDK wallet is not configured.
        :raises: ValueError: if the supplied address has a wrong format.
        """
        if not self.base_keypair:
            raise SdkNotConfiguredError('address not configured')
        validate_address(address)

        return self.channel_manager.send_transaction(lambda builder:
                                                     partial(builder.append_create_account_op, address,
                                                             starting_balance),
                                                     memo_text=memo_text)

    def trust_asset(self, asset, limit=None, memo_text=None):
        """Establish a trustline from the SDK wallet to the asset issuer.

        :param asset: the asset to establish a trustline to.
        :rtype: :class:`~stellar_base.asset.Asset`

        :param number limit: trustline limit.

        :param str memo_text: a text to put into transaction memo.

        :return: transaction hash
        :rtype: str

        :raises: :class:`~kin.SdkConfigurationError` if the SDK wallet is not configured.
        :raises: ValueError: if the issuer address has a wrong format.
        """
        if not self.base_keypair:
            raise SdkNotConfiguredError('address not configured')

        if not asset.is_native():
            try:
                validate_address(asset.issuer)
            except ValueError:
                raise ValueError('asset issuer invalid')

        return self.channel_manager.send_transaction(lambda builder:
                                                     partial(builder.append_trust_op, asset.issuer, asset.code,
                                                             limit=limit),
                                                     memo_text=memo_text)

    def check_kin_trusted(self, address):
        """Check if the account has a trustline to KIN asset.

        :param str address: the account address to query.

        :return: True if the account has a trustline to KIN asset.
        :rtype: boolean

        :raises: ValueError: if the supplied address has a wrong format.
        """
        return self.check_asset_trusted(address, KIN_ASSET)

    def check_asset_trusted(self, address, asset):
        """Check if the account has a trustline to the provided asset.

        :param str address: the account address to query.

        :return: True if the account has a trustline to the asset.
        :rtype: boolean

        :raises: ValueError: if the supplied address has a wrong format.
        :raises: ValueError: if the asset issuer address has a wrong format.
        """
        if not asset.is_native():
            try:
                validate_address(asset.issuer)
            except ValueError:
                raise ValueError('asset issuer invalid')

        acc_data = self.get_account_data(address)
        for balance in acc_data.balances:
            if balance.asset_code == asset.code and balance.asset_issuer == asset.issuer:
                return True
        return False

    def check_account_exists(self, address):
        """Check whether the account identified by the provided address exists.

        :param str address: the account address to query.

        :return: True if the account exists.

        :raises: ValueError: if the supplied address has a wrong format.
        """
        try:
            self.get_account_data(address)
            return True
        except SdkHorizonError as se:
            if se.status == 404:
                return False
            raise

    def send_lumens(self, address, amount, memo_text=None):
        """Send lumens to the account identified by the provided address.

        :param str address: the account to send lumens to.

        :param number amount: the number of lumens to send.

        :param str memo_text: a text to put into transaction memo.

        :return: transaction hash
        :rtype: str

        :raises: :class:`~kin.SdkConfigurationError` if the SDK wallet is not configured.
        :raises: ValueError: if the provided address has a wrong format.
        :raises: ValueError: if the amount is not positive.
        """
        return self.send_asset(address, Asset.native(), amount, memo_text)

    def send_kin(self, address, amount, memo_text=None):
        """Send KIN to the account identified by the provided address.

        :param str address: the account to send KIN to.

        :param number amount: the number of KIN to send.

        :param str memo_text: a text to put into transaction memo.

        :return: transaction hash
        :rtype: str

        :raises: :class:`~kin.SdkConfigurationError` if the SDK wallet is not configured.
        :raises: ValueError: if the provided address has a wrong format.
        :raises: ValueError: if the amount is not positive.
        """
        return self.send_asset(address, KIN_ASSET, amount, memo_text)

    def send_asset(self, address, asset, amount, memo_text=None):
        """Send asset to the account identified by the provided address.

        :param str address: the account to send asset to.

        :param number amount: the asset amount to send.

        :param str memo_text: a text to put into transaction memo.

        :return: transaction hash
        :rtype: str

        :raises: :class:`~kin.SdkConfigurationError` if the SDK wallet is not configured.
        :raises: ValueError: if the provided address has a wrong format.
        :raises: ValueError: if the asset issuer address has a wrong format.
        :raises: ValueError: if the amount is not positive.
        """
        if not self.base_keypair:
            raise SdkNotConfiguredError('address not configured')
        validate_address(address)

        if amount <= 0:
            raise ValueError('amount must be positive')

        if not asset.is_native():
            try:
                validate_address(asset.issuer)
            except ValueError:
                raise ValueError('asset issuer invalid')

        return self.channel_manager.send_transaction(lambda builder:
                                                     partial(builder.append_payment_op, address, amount,
                                                             asset_type=asset.code, asset_issuer=asset.issuer),
                                                     memo_text=memo_text)

    def get_account_data(self, address):
        """Gets account data.

        :param str address: the account to query.

        :return: account data
        :rtype: :class:`~kin.AccountData`

        :raises: ValueError: if the provided address has a wrong format.
        """
        validate_address(address)
        acc = self.horizon.account(address)
        check_horizon_reply(acc)

        return AccountData(acc, strict=False)

    def get_transaction_data(self, tx_hash):
        """Gets transaction data.

        :param str tx_hash: transaction hash.

        :return: transaction data
        :rtype: :class:`~kin.TransactionData`
        """
        # get transaction data
        tx = self.horizon.transaction(tx_hash)
        check_horizon_reply(tx)

        # get transaction operations
        tx_ops = self.horizon.transaction_operations(tx['hash'])  # TODO: max 50, paged?
        check_horizon_reply(tx_ops)

        tx['operations'] = tx_ops['_embedded']['records']

        return TransactionData(tx, strict=False)

    def monitor_transactions(self, callback_fn):
        """Monitor transactions related to the SDK wallet account.
        NOTE: the functions starts a background thread.

        :param callback_fn: the function to call on each received transaction. The function has one parameter,
            which is a transaction data object.
        """
        if not self.base_keypair:
            raise SdkNotConfiguredError('address not configured')
        self.monitor_address_transactions(self.get_address(), callback_fn)

    def monitor_address_transactions(self, address, callback_fn):
        """Monitor transactions related to the account identified by a provided address.
        NOTE: the functions starts a background thread.

        :param callback_fn: the function to call on each received transaction. The function has one parameter,
            which is a transaction data object.

        :raises: ValueError: if the provided address has a wrong format.
        """
        validate_address(address)

        # make the SSE request synchronous (will throw errors in the current thread)
        events = self.horizon.account_transactions(address, sse=True)  # TODO: last_id support
        # check_horizon_reply(events)  # NOTE: not a Horizon reply!  # TODO: why not consistent

        # asynchronous event processor
        def event_processor():
            import json
            for event in events:
                if event.event == 'message':
                    try:
                        tx = json.loads(event.data)

                        # get transaction operations
                        tx_ops = self.horizon.transaction_operations(tx['hash'])  # TODO: max 50, paged?
                        check_horizon_reply(tx_ops)

                        tx['operations'] = tx_ops['_embedded']['records']

                        tx_data = TransactionData(tx, strict=False)
                        callback_fn(tx_data)

                    except Exception as e:
                        logger.exception(e)
                        continue

        # start monitoring thread
        import threading
        t = threading.Thread(target=event_processor)
        t.daemon = True
        t.start()
