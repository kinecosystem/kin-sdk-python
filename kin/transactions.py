"""Contains classes and methods related to transactions and operations"""
from hashlib import sha256
from binascii import hexlify

from enum import Enum
from stellar_base.stellarxdr import Xdr

from .errors import CantSimplifyError

# This is needed in order to calculate transaction hash.
# It is the xdr representation of stellar_base.XDR.const.ENVELOP_TYPE_TX (2)
PACKED_ENVELOP_TYPE = b'\x00\x00\x00\x02'


class Transaction:
    """A transaction instance ready to be submitted"""
    # Provides a way to get the hash before sending, might be used in the future for multisig.
    def __init__(self, builder, channel_manager):
        """
        Build a transaction instance
        :param :class: `Kin.Builder` builder: The builder that contains the transaction
        :param :class: `Kin.ChannelManager` channel_manager: The channel manager that owns the builder
        """
        self.builder = builder
        self.channel_manager = channel_manager
        self.hash = self.calculate_tx_hash(builder.te, builder.te.network_id)

    def release(self):
        """
        Clear the builder and return it to the queue.
        """
        self.builder.clear()
        if self.builder not in self.channel_manager.low_balance_builders:
            self.channel_manager.channel_builders.put(self.builder)

    @staticmethod
    def calculate_tx_hash(te, network_passphrase_hash):
        """
        Calculate a tx hash.

        A tx hash is a sha256 hash of:
        1. A sha256 hash of the network_id +
        2. The xdr representation of ENVELOP_TYPE_TX +
        3. The xdr representation of the transaction
        :param te: The transaction envelop
        :param network_passphrase_hash: The network passphrase hash
        :return:
        """
        # Pack the transaction to xdr
        packer = Xdr.StellarXDRPacker()
        packer.pack_Transaction(te.to_xdr_object())
        packed_tx = packer.get_buffer()
        return hexlify(sha256(network_passphrase_hash + PACKED_ENVELOP_TYPE + packed_tx).digest()).decode()


class SimplifiedTransaction:
    def __init__(self, tx_data, kin_asset):
        self.id = tx_data.id
        self.timestamp = tx_data.created_at

        if tx_data.memo_type != 'text' and tx_data.memo_type != 'none':
            raise CantSimplifyError('Cant simplify tx with memo type: {}'.format(tx_data.memo_type))
        self.memo = tx_data.memo

        if tx_data.operation_count > 1:
            raise CantSimplifyError('Cant simplify tx with {} operations'.format(tx_data.operation_count))
        self.operation = SimplifiedOperation(tx_data.operations[0], kin_asset)

        # Override tx source with operation source if it exists.
        self.source = tx_data.operations[0].source_account or tx_data.source_account


class SimplifiedOperation:
    def __init__(self, op_data, kin_asset):
        if op_data.type == 'payment':
            # Raise error if asset is not KIN or XLM
            if op_data.asset_type != 'native':
                if op_data.asset_code != kin_asset.asset_code \
                        or op_data.asset_issuer != kin_asset.asset_issuer:
                    raise CantSimplifyError('Cant simplify operation with asset {} issued by {}'.
                                            format(op_data.asset_code, op_data.asset_issuer))

            self.asset = 'XLM' if op_data.asset_type == 'native' else op_data.asset_code
            self.amount = op_data.amount
            self.destination = op_data.to_address
            self.type = OperationTypes.PAYMENT
        elif op_data.type == 'change_trust':
            # Raise error if asset is not KIN
            if op_data.asset_code != kin_asset.asset_code \
                    or op_data.asset_issuer != kin_asset.asset_issuer:
                raise CantSimplifyError('Cant simplify operation with asset {} issued by {}'.
                                        format(op_data.asset_code, op_data.asset_issuer))

            self.type = OperationTypes.ACTIVATION
        elif op_data.type == 'create_account':
            self.destination = op_data.account
            self.starting_balance = op_data.starting_balance
            self.type = OperationTypes.CREATE_ACCOUNT
        else:
            raise CantSimplifyError('Cant simplify operation with {} operation'.format(op_data.type))


class OperationTypes(Enum):
    PAYMENT = 1
    CREATE_ACCOUNT = 2
    ACTIVATION = 3