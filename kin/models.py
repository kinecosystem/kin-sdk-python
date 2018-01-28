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
    memo_type = StringType()  # TODO: init memo
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




