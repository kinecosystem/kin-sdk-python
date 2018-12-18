"""Contains classes and methods related to transactions and operations"""
import sys
from hashlib import sha256
from binascii import hexlify
import base64

from enum import Enum
from kin_base.stellarxdr import Xdr
from kin_base.transaction import Transaction as BaseTransaction
from kin_base.transaction_envelope import TransactionEnvelope as BaseEnvelop
from kin_base.memo import TextMemo, NoneMemo
from kin_base.operation import Payment, CreateAccount
from .blockchain.channel_manager import CHANNEL_PUT_TIMEOUT

from .errors import CantSimplifyError
from .config import MEMO_TEMPLATE


# This is needed in order to calculate transaction hash.
# It is the xdr representation of kin_base.XDR.const.ENVELOP_TYPE_TX (2)
PACKED_ENVELOP_TYPE = b'\x00\x00\x00\x02'
NATIVE_ASSET_TYPE = 'native'


class SimplifiedTransaction:
    """Class to hold simplified info about a transaction"""

    def __init__(self, raw_tx):
        self.id = raw_tx.hash
        self.timestamp = raw_tx.timestamp

        # If the memo is not a text/none memo
        if not isinstance(raw_tx.tx.memo, (TextMemo, NoneMemo)):
            raise CantSimplifyError('Cant simplify tx with memo type: {}'.format(type(raw_tx.tx.memo)))
        self.memo = None if isinstance(raw_tx.tx.memo, NoneMemo) \
            else raw_tx.tx.memo.text.decode()  # will be none if the there is no memo

        if len(raw_tx.tx.operations) > 1:
            raise CantSimplifyError('Cant simplify tx with {} operations'.format(raw_tx.operation_count))
        self.operation = SimplifiedOperation(raw_tx.tx.operations[0])

        # Override tx source with operation source if it exists.
        self.source = raw_tx.tx.operations[0].source or raw_tx.tx.source.decode()


class SimplifiedOperation:
    """Class to hold simplified info about a operation"""

    def __init__(self, op_data):
        if isinstance(op_data, Payment):
            # Raise error if its not a KIN payment
            if op_data.asset.type != NATIVE_ASSET_TYPE:
                raise CantSimplifyError('Cant simplify operation with asset {} issued by {}'.
                                        format(op_data.asset.code, op_data.asset.issuer))

            self.amount = float(op_data.amount)
            self.destination = op_data.destination
            self.type = OperationTypes.PAYMENT

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
        # Network_id is left as '' since we override the hash anyway
        self.tx = decode_transaction(horizon_tx_response['envelope_xdr'], network_id='', simple=False)
        self.timestamp = horizon_tx_response['created_at']
        self.hash = horizon_tx_response['hash']


class OperationTypes(Enum):
    """Possible operation types for a simple operation"""

    PAYMENT = 1
    CREATE_ACCOUNT = 2


def build_memo(app_id, memo):
    """
    Build a memo for a tx that fits the pre-defined template
    :param app_id: The app_id to include in the memo
    :param memo: The memo to include
    :return: the finished memo
    :rtype: str
    """
    finished_memo = MEMO_TEMPLATE.format(app_id)
    if memo is not None:
        finished_memo += memo

    return finished_memo


def decode_transaction(b64_tx, network_id, simple=True):
    """
    Decode a base64 transaction envelop
    :param str b64_tx: a transaction envelop encoded in base64
    :param boolean simple: should the tx be simplified
    :param network_id: the network_id for the transaction
    :return: The transaction
    :rtype kin.SimplifiedTransaction | kin_base.Transaction
    :raises: KinErrors.CantSimplifyError: if the tx cannot be simplified
    """
    unpacker = Xdr.StellarXDRUnpacker(base64.b64decode(b64_tx))
    envelop = unpacker.unpack_TransactionEnvelope()
    envelop.tx = BaseTransaction.from_xdr_object(envelop.tx)
    passphrase_hash = sha256(network_id.encode()).digest()
    base_tx = BaseEnvelop.from_xdr(b64_tx).tx

    envelop.hash = calculate_tx_hash(base_tx, passphrase_hash)

    # Time cannot be extracted from the envelop
    envelop.timestamp = None
    if simple:
        return SimplifiedTransaction(envelop)
    return envelop.tx


def calculate_tx_hash(tx, network_passphrase_hash):
    """
    Calculate a tx hash.

    A tx hash is a sha256 hash of:
    1. A sha256 hash of the network_id +
    2. The xdr representation of ENVELOP_TYPE_TX +
    3. The xdr representation of the transaction
    :param tx: The builder's transaction object
    :param network_passphrase_hash: The network passphrase hash
    :return:
    """
    # Pack the transaction to xdr
    packer = Xdr.StellarXDRPacker()
    packer.pack_Transaction(tx.to_xdr_object())
    packed_tx = packer.get_buffer()
    return hexlify(sha256(network_passphrase_hash + PACKED_ENVELOP_TYPE + packed_tx).digest()).decode()
