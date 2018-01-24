# -*- coding: utf-8 -*

# Copyright (C) 2018 Kin Foundation

from decimal import Decimal
from threading import Lock

from stellar_base.address import Address
from stellar_base.asset import Asset
from stellar_base.horizon import Horizon, horizon_testnet, horizon_livenet
from stellar_base.keypair import Keypair

from .builder import Builder
from .exceptions import (
    SdkConfigurationError,
    SdkNotConfiguredError,
    SdkHorizonError,
)
from .utils import validate_address, check_horizon_reply

import logging
logger = logging.getLogger(__name__)

KIN_ISSUER = 'GDVDKQFP665JAO7A2LSHNLQIUNYNAAIGJ6FYJVMG4DT3YJQQJSRBLQDG'  # TODO: real address
KIN_ASSET = Asset('KIN', KIN_ISSUER)

DEFAULT_STARTING_BALANCE = 200

# default request retry configuration (linear backoff).
RETRY_ATTEMPTS = 3
RETRY_DELAY = 0.3


# noinspection PyClassHasNoInit
class TransactionStatus:
    """Transaction status enumerator."""
    UNKNOWN = 0
    PENDING = 1
    SUCCESS = 2
    FAIL = 3


class PrintableObject(object):
    def __str__(self):
        sb = []
        for key in self.__dict__:
            if not key.startswith('__'):
                sb.append("\t{key}='{value}'".format(key=key, value=self.__dict__[key]))
        return '\n'.join(sb)

    def __repr__(self):
        return self.__str__()


class OperationData(PrintableObject):
    """Operation data holder"""
    id = None
    source_account = None
    type = None
    created_at = None
    transaction_hash = None
    asset_type = None
    asset_code = None
    asset_issuer = None
    limit = None
    trustor = None
    trustee = None
    from_address = None
    to_address = None
    amount = None


class TransactionData(PrintableObject):
    """Transaction data holder"""
    hash = None
    created_at = None
    source_account = None
    sequence = None
    operations = []
    time_bounds = []
    memo = None
    fee = None
    signatures = []


class AccountData(PrintableObject):
    """Account data holder"""

    #class Struct:
    #    """Handy variable holder"""
    #    def __init__(self, **entries): self.__dict__.update(entries)

    class Thresholds(object):
        def __init__(self, low, medium, high):
            self.low = low
            self.medium = medium
            self.high = high

    id = None
    sequence = None
    thresholds = None
    balances = None
    signers = None
    data = None


class SDK(object):
    """
    The :class:`~kin.SDK` class is the primary interface to the KIN Python SDK based on Stellar Blockchain.
    It maintains a connection context with a Horizon node and hides all the specifics of dealing with Stellar REST API.
    """

    def __init__(self, seed='', horizon_endpoint_uri='', testnet=False):
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

        if testnet:
            self.network = 'TESTNET'
        else:
            self.network = 'PUBLIC'

        if horizon_endpoint_uri:
            self.horizon = Horizon(horizon_endpoint_uri)
        else:
            if testnet:
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
            except:
                raise
            finally:
                self.builder.clear()

    def trust_asset(self, asset, limit=None, source=None):
        if not asset.code:
            raise ValueError('asset code invalid')
        if not self.keypair:
            raise SdkNotConfiguredError('address not configured')
        validate_address(asset.issuer)

        with self.builder_lock:
            try:
                self.builder.append_trust_op(asset.issuer, asset.code, limit=limit, source=source)
                self.builder.sign()
                reply = self.builder.submit()
                check_horizon_reply(reply)
                return reply.get('hash')
            except:
                raise
            finally:
                self.builder.clear()

    def check_asset_trusted(self, address, asset):
        addr = Address(address=address, network=self.network, horizon=self.horizon.horizon)
        addr.get()  # TODO: exception handling?
        for balance in addr.balances:
            if balance.get('asset_code') == asset.code and balance.get('asset_issuer') == asset.issuer:
                return True
        return False

    def check_account_exists(self, address):
        addr = Address(address=address, network=self.network, horizon=self.horizon.horizon)
        try:
            addr.get()
            return True
        except:
            return False

    def send_lumen(self, address, amount, source=None, memo=None):
        return self.send_asset(address, Asset('XLM'), amount, source, memo)

    def send_kin(self, address, amount, source=None, memo=None):
        return self.send_asset(address, KIN_ASSET, amount, source, memo)

    def send_asset(self, address, asset, amount, source=None, memo=None):
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
                if memo:
                    self.builder.add_text_memo(memo[:28])  # max memo length is 28
                self.builder.sign()
                reply = self.builder.submit()
                check_horizon_reply(reply)
                return reply
            except:
                raise
            finally:
                self.builder.clear()

    def get_account_data(self, address):
        addr = Address(address=address, network=self.network, horizon=self.horizon.horizon)
        addr.get()  # will raise AccountNotExistsError. TODO: good?
        acc_data = AccountData()
        acc_data.id = address

        '''
        self.sequence = None
        self.balances = None
        self.paging_token = None
        self.thresholds = None
        self.flags = None
        self.signers = None
        self.data = None
            id = None
    sequence = None
    data = None
    thresholds = None
    balances = None
    signers = None
        '''

    def get_transaction_data(self, tx_hash):
        """Gets transaction data.

        :param str tx_hash: transaction hash
        :return: transaction data
        :rtype: :class:`~kin.TransactionData`
        """
        tx = self.horizon.transaction(tx_hash)
        check_horizon_reply(tx)

        tx_data = TransactionData()
        tx_data.hash = tx.get('hash')
        tx_data.created_at = tx.get('created_at')
        tx_data.source_account = tx.get('source_account')
        tx_data.sequence = tx.get('source_account_sequence')
        tx_data.operations = []
        tx_data.fee = tx.get('fee_paid')
        tx_data.signatures = tx.get('signatures')
        tx_data.memo = None  # TODO

        tx_ops = self.horizon.transaction_operations(tx_hash)  # TODO: max 50, paged?
        check_horizon_reply(tx_ops)
        for tx_op in tx_ops.get('_embedded').get('records'):
            op_data = OperationData()
            op_data.id = tx_op.get('id')
            op_data.source_account = tx_op.get('source_account')
            op_data.type = tx_op.get('type')
            op_data.created_at = tx_op.get('created_at')
            op_data.transaction_hash = tx_op.get('transaction_hash')
            op_data.asset_type = tx_op.get('asset_type')
            op_data.asset_code = tx_op.get('asset_code')
            op_data.asset_issuer = tx_op.get('asset_issuer')
            op_data.trustor = tx_op.get('trustor')
            op_data.trustee = tx_op.get('trustee')
            op_data.from_address = tx_op.get('from')
            op_data.to_address = tx_op.get('to')
            amount = tx_op.get('amount')
            if amount:
                op_data.amount = Decimal(amount)
            limit = tx_op.get('limit')
            if limit:
                op_data.limit = Decimal(limit)
            tx_data.operations.append(op_data)

        return tx_data

    # helpers

