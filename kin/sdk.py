# -*- coding: utf-8 -*

# Copyright (C) 2018 Kin Foundation

from decimal import Decimal, getcontext
from threading import Lock

from stellar_base.address import Address
from stellar_base.asset import Asset
from stellar_base.horizon import Horizon, horizon_testnet, horizon_livenet
from stellar_base.keypair import Keypair
from stellar_base.utils import AccountNotExistError

from .builder import Builder
from .exceptions import (
    SdkConfigurationError,
    SdkNotConfiguredError,
    SdkHorizonError,
)
from models import AccountData, TransactionData
from .utils import validate_address, check_horizon_reply

import logging
logger = logging.getLogger(__name__)

getcontext().prec = 7  # IMPORTANT: XLM precision

KIN_ISSUER = 'GDVDKQFP665JAO7A2LSHNLQIUNYNAAIGJ6FYJVMG4DT3YJQQJSRBLQDG'  # TODO: real address
KIN_ASSET = Asset('KIN', KIN_ISSUER)

DEFAULT_STARTING_BALANCE = 200

# default request retry configuration (linear backoff).
RETRY_ATTEMPTS = 3
RETRY_DELAY = 0.3


class SDK(object):
    """
    The :class:`~kin.SDK` class is the primary interface to the KIN Python SDK based on Stellar Blockchain.
    It maintains a connection context with a Horizon node and hides all the specifics of dealing with Stellar REST API.
    """

    def __init__(self, seed='', horizon_endpoint_uri='', network='PUBLIC'):
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

        if network:
            self.network = network
        else:
            self.network = 'TESTNET'

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

        self.keypair = None
        if seed:
            self.keypair = Keypair.from_seed(seed)
            # create a first builder, load the sequence from our account
            self.builder = Builder(secret=seed, network=self.network, horizon=self.horizon.horizon)
            self.builder_lock = Lock()

    def get_address(self):
        """Get public address of the SDK wallet.
        The wallet is configured by a private key supplied in during SDK initialization.

        :returns: public address of the wallet.
        :rtype: str

        :raises: :class:`~kin.exceptions.SdkConfigurationError`: if the SDK was not configured with a private key.
        """
        if not self.keypair:
            raise SdkNotConfiguredError('address not configured')
        return self.keypair.address().decode()

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
        validate_address(address)
        addr = Address(address=address, network=self.network, horizon=self.horizon.horizon)
        addr.get()  # TODO: exception handling

        for b in addr.balances:
            if (b.get('asset_type') == 'native' and asset.code == 'XLM') \
                    or (b.get('asset_code') == asset.code and b.get('asset_issuer') == asset.issuer):
                return Decimal(b.get('balance'))
        return 0

    def create_account(self, address, starting_balance=DEFAULT_STARTING_BALANCE, source=None):
        if not self.keypair:
            raise SdkNotConfiguredError('address not configured')
        validate_address(address)

        with self.builder_lock:
            try:
                self.builder.append_create_account_op(address, starting_balance, source=source)
                self.builder.sign()
                reply = self.builder.submit()
                check_horizon_reply(reply)
                return reply.get('hash')
            finally:
                self.builder.clear()

    def trust_kin(self, limit=None, source=None):
        return self.trust_asset(KIN_ASSET, limit, source)

    def trust_asset(self, asset, limit=None, source=None):
        if not self.keypair:
            raise SdkNotConfiguredError('address not configured')
        try:
            validate_address(asset.issuer)
        except:
            raise ValueError('asset issuer invalid')

        with self.builder_lock:
            try:
                self.builder.append_trust_op(asset.issuer, asset.code, limit=limit, source=source)
                self.builder.sign()
                reply = self.builder.submit()
                check_horizon_reply(reply)
                return reply.get('hash')
            finally:
                self.builder.clear()

    def check_kin_trusted(self, address):
        return self.check_asset_trusted(address, KIN_ASSET)

    def check_asset_trusted(self, address, asset):
        validate_address(address)

        addr = Address(address=address, network=self.network, horizon=self.horizon.horizon)
        addr.get()  # TODO: exception handling?
        for balance in addr.balances:
            if balance.get('asset_code') == asset.code and balance.get('asset_issuer') == asset.issuer:
                return True
        return False

    def check_account_exists(self, address):
        validate_address(address)

        addr = Address(address=address, network=self.network, horizon=self.horizon.horizon)
        try:
            addr.get()
            return True
        except AccountNotExistError:
            return False

    def send_lumens(self, address, amount, source=None, memo=None):
        return self.send_asset(address, Asset('XLM'), amount, source, memo)

    def send_kin(self, address, amount, source=None, memo=None):
        return self.send_asset(address, KIN_ASSET, amount, source, memo)

    def send_asset(self, address, asset, amount, source=None, memo_text=None):
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
        if not self.keypair:
            raise SdkNotConfiguredError('address not configured')
        validate_address(address)
        if amount <= 0:
            raise ValueError('amount must be positive')

        with self.builder_lock:
            try:
                self.builder.append_payment_op(address, amount, asset_type=asset.code, asset_issuer=asset.issuer, source=source)
                if memo_text:
                    self.builder.add_text_memo(memo_text[:28])  # max memo length is 28
                self.builder.sign()
                reply = self.builder.submit()
                check_horizon_reply(reply)
                return reply.get('hash')
            finally:
                self.builder.clear()

    def get_account_data(self, address):
        """Gets account data.

        :param str address: account address
        :return: account data
        :rtype: :class:`~kin.AccountData`
        """
        # Address.get()
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


