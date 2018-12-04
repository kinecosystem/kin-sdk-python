"""Contains data models related to horizon"""

from schematics.models import Model
from schematics.types import IntType, BooleanType, StringType, UTCDateTimeType, FloatType
from schematics.types.compound import ModelType, ListType, DictType


class PModel(Model):
    """Base class for our models that provides printout capabilities"""

    def __str__(self):
        sb = []
        for key in self.__dict__:
            if not key.startswith('__'):
                sb.append("\t{}='{}'".format(key, self.__dict__[key]))
        return '\n'.join(sb)

    def __repr__(self):
        return self.__str__()

    def __hash__(self):
        return hash(self.__str__())


class AccountData(PModel):
    class Thresholds(PModel):
        low_threshold = IntType(default=0)
        med_threshold = IntType(default=0)
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
        balance = FloatType(default=0)
        limit = FloatType()

    class Signer(PModel):
        public_key = StringType()
        key = StringType()
        weight = IntType()
        signature_type = StringType(serialized_name='type')

    id = StringType()
    account_id = StringType()
    sequence = StringType()
    data = DictType(StringType, default={})
    thresholds = ModelType(Thresholds)
    balances = ListType(ModelType(Balance), default=[])
    flags = ModelType(Flags)
    paging_token = StringType()
    subentry_count = IntType()
    signers = ListType(ModelType(Signer), default=[])


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
