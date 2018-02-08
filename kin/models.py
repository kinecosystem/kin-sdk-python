# -*- coding: utf-8 -*

# Copyright (C) 2018 Kin Foundation


from schematics.models import Model
from schematics.types import IntType, BooleanType, DecimalType, StringType, UTCDateTimeType
from schematics.types.compound import ModelType, ListType, DictType


class AccountData(Model):
    class Thresholds(Model):
        low_threshold = IntType(default=0)
        medium_threshold = IntType(default=0)
        high_threshold = IntType(default=0)

    class Flags(Model):
        auth_required = BooleanType(default=False)
        auth_revocable = BooleanType(default=False)

    class Balance(Model):
        asset_type = StringType()
        asset_code = StringType()
        asset_issuer = StringType()
        balance = DecimalType(default=0)
        limit = DecimalType()  # TODO: max value?

    id = StringType()  # TODO: min, max length?
    sequence = StringType()
    data = DictType(StringType, default={})
    thresholds = ModelType(Thresholds)
    balances = ListType(ModelType(Balance), default=[])
    flags = ModelType(Flags)
    # subentry_count
    # paging_token
    # signers


class TransactionData(Model):
    class OperationData(Model):
        id = StringType()
        source_account = StringType()
        type = StringType()
        created_at = UTCDateTimeType()
        transaction_hash = StringType()
        asset_type = StringType()  # TODO: enums?
        asset_code = StringType()  # TODO: min, max length?
        asset_issuer = StringType()
        limit = DecimalType()
        trustor = StringType()
        trustee = StringType()
        from_address = StringType()
        to_address = StringType()
        amount = DecimalType()

    hash = StringType()  # TODO: min, max length?
    created_at = UTCDateTimeType()
    source_account = StringType()  # TODO: min, max length?
    source_account_sequence = StringType()
    operations = ListType(ModelType(OperationData), default=[])
    memo_type = StringType()
    memo = StringType()
    fee_paid = DecimalType()
    signatures = ListType(StringType, default=[])
    # id
    # paging_token
    # envelope_xdr
    # time_bounds
    # ledger
    # _links
    # result_xdr
    # result_meta_xdr
    # operation_count
    # fee_meta_xdr

    # TODO: do it properly
    def __str__(self):
        sb = []
        for key in self.__dict__:
            if not key.startswith('__'):
                sb.append("\t{key}='{value}'".format(key=key, value=self.__dict__[key]))
        return '\n'.join(sb)

    def __repr__(self):
        return self.__str__()


class TransactionResultCodes(Model):
    transaction = StringType()
    operations = ListType(StringType, default=[])


class FailedTransactionExtras(Model):
    envelope_xdr = StringType()
    result_xdr = StringType()
    result_codes = ModelType(TransactionResultCodes)


class HTTPProblemDetails(Model):
    """HTTP Problem Details object.
    See https://tools.ietf.org/html/rfc7807
    """
    type = StringType()
    title = StringType()
    status = IntType()
    detail = StringType()
    instance = StringType()
    extras = ModelType(FailedTransactionExtras)
