# -*- coding: utf-8 -*

# Copyright (C) 2018 Kin Foundation

from decimal import Decimal, getcontext
from functools import partial

from stellar_base.asset import Asset
from stellar_base.horizon import Horizon, horizon_testnet, horizon_livenet
from stellar_base.keypair import Keypair

from .channel_manager import ChannelManager
from .exceptions import (
    SdkConfigurationError,
    SdkNotConfiguredError,
    SdkHorizonError,
)
from .models import AccountData, TransactionData
from .utils import validate_address, check_horizon_reply

import logging
logger = logging.getLogger(__name__)

getcontext().prec = 7  # IMPORTANT: XLM decimal precision

KIN_ISSUER = 'GDVDKQFP665JAO7A2LSHNLQIUNYNAAIGJ6FYJVMG4DT3YJQQJSRBLQDG'  # TODO: real address
KIN_ASSET = Asset('KIN', KIN_ISSUER)

# https://www.stellar.org/developers/guides/concepts/fees.html
BASE_RESERVE = 0.5  # in XLM
MIN_ACCOUNT_BALANCE = (2 + 1) * BASE_RESERVE  # 1 additional trustline op

# default request retry configuration (linear backoff).
RETRY_ATTEMPTS = 3
RETRY_DELAY = 0.3


class SDK(object):
    """
    The :class:`~kin.SDK` class is the primary interface to the KIN Python SDK based on Stellar Blockchain.
    It maintains a connection context with a Horizon node and hides all the specifics of dealing with Stellar REST API.
    """

    def __init__(self, base_seed='', horizon_endpoint_uri='', network='PUBLIC', channel_seeds=[]):
        """Create a new instance of the KIN SDK for Stellar.

        The SDK needs a JSON-RPC provider, contract definitions and the wallet private key.

        If private_key is not provided, the SDK can still be used in "anonymous" mode with only the following
        functions available:
            - get_address_ether_balance
            - get_transaction_status
            - monitor_ether_transactions

        :param str private_key: a private key to initialize the wallet with. If either private key or keyfile
            are not provided, the wallet will not be initialized and methods needing the wallet will raise exception.

        :param str keyfile: the path to the keyfile to initialize to wallet with. Usually you will also need to supply
        a password for this keyfile.

        :param str password: a password for the keyfile.

        :param provider: JSON-RPC provider to work with. If not provided, a default `web3:providers:HTTPProvider`
            is used, inited with provider_endpoint_uri.
        :type provider: :class:`web3:providers:BaseProvider`

        :param str provider_endpoint_uri: a URI to use with a default HTTPProvider. If not provided, a
            default endpoint will be used.

        :param str contract_address: the address of the token contract. If not provided, a default KIN
            contract address will be used.

        :param dict contract_abi: The contract ABI. If not provided, a default KIN contract ABI will be used.

        :returns: An instance of the SDK.
        :rtype: :class:`~kin.TokenSDK`

        :raises: :class:`~kin.exceptions.SdkConfigurationError` if some of the configuration parameters are invalid.
        """

        self.network = network
        if not self.network:
            self.network = 'PUBLIC'

        if horizon_endpoint_uri:
            self.horizon = Horizon(horizon_endpoint_uri)
        else:
            if self.network == 'TESTNET':
                self.horizon = horizon_testnet()
            else:
                self.horizon = horizon_livenet()

        # check Horizon connection
        try:
            self.horizon.query('')
        except Exception as e:
            raise SdkConfigurationError('cannot connect to horizon')

        # init sdk account base_keypair if a base_seed is supplied
        self.base_keypair = None
        if base_seed:
            self.base_keypair = Keypair.from_seed(base_seed)
            # init channel manager
            if not channel_seeds:
                channel_seeds = [base_seed]
            self.channel_manager = ChannelManager(base_seed, channel_seeds, self.network, self.horizon.horizon)

    def get_address(self):
        """Get public address of the SDK wallet.
        The wallet is configured by a private key supplied in during SDK initialization.

        :returns: public address of the wallet.
        :rtype: str

        :raises: :class:`~kin.exceptions.SdkConfigurationError`: if the SDK was not configured with a private key.
        """
        if not self.base_keypair:
            raise SdkNotConfiguredError('address not configured')
        return self.base_keypair.address().decode()

    def get_lumen_balance(self):
        """Get XLM balance of the SDK wallet.
        The wallet is configured by a private key supplied in during SDK initialization.

        :returns: : the balance in Ether of the internal wallet.
        :rtype: Decimal

        :raises: :class:`~kin.exceptions.SdkConfigurationError`: if the SDK was not configured with a private key.
        """
        return self.get_address_lumen_balance(self.get_address())

    def get_kin_balance(self):
        """Get KIN balance of the SDK wallet.
        The wallet is configured by a private key supplied in during SDK initialization.

        :returns: : the balance in KIN of the internal wallet.
        :rtype: Decimal

        :raises: :class:`~kin.exceptions.SdkConfigurationError`: if the SDK was not configured with a private key.
        """
        return self.get_address_kin_balance(self.get_address())

    def get_address_lumen_balance(self, address):
        """Get XLM balance of a public address.

        :param: str address: a public address to query.

        :returns: the balance in Ether of the provided address.
        :rtype: Decimal

        :raises: ValueError: if the supplied address has a wrong format.
        """
        return self.get_address_asset_balance(address, Asset('XLM'))

    def get_address_kin_balance(self, address):
        """Get KIN balance of a public address.

        :param: str address: a public address to query.

        :returns: : the balance in KIN of the provided address.
        :rtype: Decimal

        :raises: ValueError: if the supplied address has a wrong format.
        """
        return self.get_address_asset_balance(address, KIN_ASSET)

    def get_address_asset_balance(self, address, asset):
        acc_data = self.get_account_data(address)
        for balance in acc_data.balances:
            if (balance.asset_type == 'native' and asset.code == 'XLM') \
                    or (balance.asset_code == asset.code and balance.asset_issuer == asset.issuer):
                return balance.balance
        return 0

    def create_account(self, address, starting_balance=MIN_ACCOUNT_BALANCE, memo_text=None):
        if not self.base_keypair:
            raise SdkNotConfiguredError('address not configured')
        validate_address(address)

        return self.channel_manager.send_transaction(lambda builder:
                                                     partial(builder.append_create_account_op, address,
                                                             starting_balance),
                                                     memo_text=memo_text)

    def trust_kin(self, limit=None):
        return self.trust_asset(KIN_ASSET, limit)

    def trust_asset(self, asset, limit=None, memo_text=None):
        if not self.base_keypair:
            raise SdkNotConfiguredError('address not configured')
        try:
            validate_address(asset.issuer)
        except:
            raise ValueError('asset issuer invalid')

        return self.channel_manager.send_transaction(lambda builder:
                                                     partial(builder.append_trust_op, asset.issuer, asset.code,
                                                             limit=limit),
                                                     memo_text=memo_text)

    def check_kin_trusted(self, address):
        return self.check_asset_trusted(address, KIN_ASSET)

    def check_asset_trusted(self, address, asset):
        acc_data = self.get_account_data(address)
        for balance in acc_data.balances:
            if balance.asset_code == asset.code and balance.asset_issuer == asset.issuer:
                return True
        return False

    def check_account_exists(self, address):
        try:
            self.get_account_data(address)
            return True
        except SdkHorizonError as se:
            if se.status == 404:
                return False
            raise

    def send_lumens(self, address, amount, memo_text=None):
        return self.send_asset(address, Asset('XLM'), amount, memo_text)

    def send_kin(self, address, amount, memo_text=None):
        return self.send_asset(address, KIN_ASSET, amount, memo_text)

    def send_asset(self, address, asset, amount, memo_text=None):
        """Send tokens from my wallet to address.

        :param str address: the address to send tokens to.

        :param float amount: the amount of tokens to transfer.

        :returns: transaction id
        :rtype: str

        :raises: :class:`~kin.exceptions.SdkConfigurationError`: if the SDK was not configured with a private key.
        :raises: ValueError: if the amount is not positive.
        :raises: ValueError: if the nonce is incorrect.
        :raises: ValueError if insufficient funds for for gas * price.
        """
        if not self.base_keypair:
            raise SdkNotConfiguredError('address not configured')
        validate_address(address)
        if amount <= 0:
            raise ValueError('amount must be positive')

        return self.channel_manager.send_transaction(lambda builder:
                                                     partial(builder.append_payment_op, address, amount,
                                                             asset_type=asset.code, asset_issuer=asset.issuer),
                                                     memo_text=memo_text)

    def get_account_data(self, address):
        """Gets account data.

        :param str address: account address
        :return: account data
        :rtype: :class:`~kin.AccountData`
        """
        validate_address(address)
        acc = self.horizon.account(address)
        check_horizon_reply(acc)

        return AccountData(acc, strict=False)

    def get_transaction_data(self, tx_hash):
        """Gets transaction data.

        :param str tx_hash: transaction hash
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
        """Monitor transactions related to the sdk account"""
        if not self.base_keypair:
            raise SdkNotConfiguredError('address not configured')
        self.monitor_address_transactions(self.get_address(), callback_fn)

    def monitor_address_transactions(self, address, callback_fn):
        """Monitor transactions related to specific acccount"""

        # make the SSE request synchronous (will throw errors in the current thread)
        events = self.horizon.account_transactions(address, sse=True)  # TODO: last_id support

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
