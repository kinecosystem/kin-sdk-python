"""Contains classes and methods related to transactions and operations"""
import sys
from hashlib import sha256
from binascii import hexlify
import base64

from enum import Enum
from stellar_base.stellarxdr import Xdr
from stellar_base.transaction import Transaction as BaseTransaction
from stellar_base.memo import TextMemo, NoneMemo
from stellar_base.operation import Payment, ChangeTrust, CreateAccount

from .errors import CantSimplifyError, MemoTooLongError
from .config import MEMO_TEMPLATE, MEMO_CAP


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
        self.hash = self.calculate_tx_hash(builder.tx, builder.te.network_id)

    def release(self):
        """
        Clear the builder and return it to the queue.
        """
        self.builder.clear()
        if self.builder not in self.channel_manager.low_balance_builders:
            self.channel_manager.channel_builders.put(self.builder, timeout=0.5)

    @staticmethod
    def calculate_tx_hash(tx, network_passphrase_hash):
        """
        Calculate a tx hash.

        A tx hash is a sha256 hash of:
        1. A sha256 hash of the network_id +
        2. The xdr representation of ENVELOP_TYPE_TX +
        3. The xdr representation of the transaction
        :param te: The builder's transaction object
        :param network_passphrase_hash: The network passphrase hash
        :return:
        """
        # Pack the transaction to xdr
        packer = Xdr.StellarXDRPacker()
        packer.pack_Transaction(tx.to_xdr_object())
        packed_tx = packer.get_buffer()
        return hexlify(sha256(network_passphrase_hash + PACKED_ENVELOP_TYPE + packed_tx).digest()).decode()


class SimplifiedTransaction:
    """Class to hold simplified info about a transaction"""

    def __init__(self, raw_tx, kin_asset):
        self.id = raw_tx.hash
        self.timestamp = raw_tx.timestamp
        self.operations = []

        # If the memo is not a text/none memo
        if not isinstance(raw_tx.tx.memo, (TextMemo, NoneMemo)):
            raise CantSimplifyError('Cant simplify tx with memo type: {}'.format(type(raw_tx.tx.memo)))
        self.memo = None if isinstance(raw_tx.tx.memo, NoneMemo) \
            else raw_tx.tx.memo.text.decode() # will be none if the there is no memo

        for operation in raw_tx.tx.operations:
            self.operations.append(SimplifiedOperation(operation, kin_asset))

        # Override tx source with operation source if it exists.
        self.source = raw_tx.tx.operations[0].source or raw_tx.tx.source.decode()


class SimplifiedOperation:
    """Class to hold simplified info about a operation"""

    def __init__(self, op_data, kin_asset):
        if isinstance(op_data, Payment):
            # Raise error if asset is not KIN or XLM
            if op_data.asset.type != 'native':
                if op_data.asset.code != kin_asset.code \
                        or op_data.asset.issuer != kin_asset.issuer:
                    raise CantSimplifyError('Cant simplify operation with asset {} issued by {}'.
                                            format(op_data.asset.code, op_data.asset.issuer))

            self.asset = 'XLM' if op_data.asset.type == 'native' else op_data.asset.code
            self.amount = float(op_data.amount)
            self.destination = op_data.destination
            self.type = OperationTypes.PAYMENT
        elif isinstance(op_data, ChangeTrust):
            # Raise error if asset is not KIN
            if op_data.line.code != kin_asset.code \
                    or op_data.line.issuer != kin_asset.issuer:
                raise CantSimplifyError('Cant simplify operation with asset {} issued by {}'.
                                        format(op_data.line.code, op_data.line.issuer))

            self.type = OperationTypes.ACTIVATION
        elif isinstance(op_data, CreateAccount):
            self.destination = op_data.destination
            self.starting_balance = float(op_data.starting_balance)
            self.type = OperationTypes.CREATE_ACCOUNT
        else:
            raise CantSimplifyError('Cant simplify operation with {} operation'.format(op_data.type))


class RawTransaction:
    """Class to hold raw info about a transaction"""
    def __init__(self, horizon_tx_response):
        """
        :param dict horizon_tx_response: the json response from an horizon query
        """
        unpacker = Xdr.StellarXDRUnpacker(base64.b64decode(horizon_tx_response['envelope_xdr']))
        envelop = unpacker.unpack_TransactionEnvelope()
        self.tx = BaseTransaction.from_xdr_object(envelop.tx)
        self.timestamp = horizon_tx_response['created_at']
        self.hash = horizon_tx_response['hash']


class OperationTypes(Enum):
    """Possible operation types for a simple operation"""

    PAYMENT = 1
    CREATE_ACCOUNT = 2
    ACTIVATION = 3


def build_memo(app_id, memo):
    """
    Build a memo for a tx that fits the pre-defined template
    :param memo: The memo to include
    :return: the finished memo
    :rtype: str
    """
    finished_memo = MEMO_TEMPLATE.format(app_id)
    if memo is not None:
        finished_memo += memo

    # Need to count the length in bytes
    if sys.version[0] == '2':  # python 2
        if len(finished_memo) > MEMO_CAP:
            raise MemoTooLongError('{} > {}'.format(len(finished_memo), MEMO_CAP))

    elif len(finished_memo.encode()) > MEMO_CAP:
        raise MemoTooLongError('{} > {}'.format(len(finished_memo), MEMO_CAP))

    return finished_memo
