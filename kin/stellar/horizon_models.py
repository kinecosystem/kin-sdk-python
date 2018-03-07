# -*- coding: utf-8 -*

# Copyright (C) 2018 Kin Foundation


from schematics.models import Model
from schematics.types import IntType, BooleanType, DecimalType, StringType, UTCDateTimeType
from schematics.types.compound import ModelType, ListType, DictType


class PModel(Model):
    def __str__(self):
        sb = []
        for key in self.__dict__:
            if not key.startswith('__'):
                sb.append("\t{}='{}'".format(key, self.__dict__[key]))
        return '\n'.join(sb)

    def __repr__(self):
        return self.__str__()


class AccountData(PModel):
    class Thresholds(PModel):
        low_threshold = IntType(default=0)
        medium_threshold = IntType(default=0)
        high_threshold = IntType(default=0)

    class Flags(PModel):
        """Flags set on issuer accounts.
           TrustLines are created with authorized set to "false" requiring
           the issuer to set it for each TrustLine
        """
        auth_required = BooleanType(default=False)  # If set, the authorized flag in TrustLines can be cleared.
        # Otherwise, authorization cannot be revoked
        auth_revocable = BooleanType(default=False)  # Once set, causes all AUTH_* flags to be read-only

    class Balance(PModel):
        asset_type = StringType()
        asset_code = StringType()
        asset_issuer = StringType()
        balance = DecimalType(default=0)
        limit = DecimalType()

    id = StringType()
    sequence = StringType()
    data = DictType(StringType, default={})
    thresholds = ModelType(Thresholds)
    balances = ListType(ModelType(Balance), default=[])
    flags = ModelType(Flags)
    # paging_token
    # subentry_count
    # signers


class OperationData(PModel):
    id = StringType()
    source_account = StringType()
    type = StringType()
    created_at = UTCDateTimeType()
    transaction_hash = StringType()
    asset_type = StringType()
    asset_code = StringType()
    asset_issuer = StringType()
    limit = DecimalType()
    trustor = StringType()
    trustee = StringType()
    from_address = StringType(serialized_name='from')
    to_address = StringType(serialized_name='to')
    amount = DecimalType()


class TransactionData(PModel):
    id = StringType()
    hash = StringType()
    created_at = UTCDateTimeType()
    source_account = StringType()
    source_account_sequence = StringType()
    operations = ListType(ModelType(OperationData), default=[])
    ledger = StringType()
    memo_type = StringType()
    memo = StringType()
    fee_paid = DecimalType()
    signatures = ListType(StringType, default=[])
    paging_token = StringType()
    # time_bounds
    # operation_count
    # envelope_xdr
    # result_xdr
    # result_meta_xdr
    # fee_meta_xdr


class TransactionResultCodes(PModel):
    transaction = StringType()
    operations = ListType(StringType, default=[])


class HTTPProblemDetails(PModel):
    """HTTP Problem Details object.
    See https://tools.ietf.org/html/rfc7807
    """
    class Extras(PModel):
        invalid_field = StringType()
        envelope_xdr = StringType()
        result_xdr = StringType()
        result_codes = ModelType(TransactionResultCodes)

    type = StringType()
    title = StringType()
    status = IntType()
    detail = StringType()
    instance = StringType()
    extras = ModelType(Extras)
