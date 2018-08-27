"""Contains classes and methods related to transactions and operations"""
from enum import Enum

from .errors import CantSimplifyError


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