# -*- coding: utf-8 -*

# Copyright (C) 2018 Kin Foundation

from .models import HTTPProblemDetails


# All exceptions should subclass from SdkError in this module.
class SdkError(Exception):
    """Base class for all SDK errors."""
    #def __init__(self, msg):
    #    super(SdkError, self).__init__(msg)


class SdkConfigurationError(SdkError):
    pass


class SdkNotConfiguredError(SdkError):
    pass


class SdkHorizonError(SdkError, HTTPProblemDetails):
    def __init__(self, dict):
        super(HTTPProblemDetails, self).__init__(dict, strict=False)

    def __str__(self):
        if self.extras and self.extras.result_codes and self.extras.result_codes.operations:
            return repr(self.extras.result_codes.operations[0])
        return repr(self.title)


# result codes from github.com/stellar/horizon/codes/main.go


# noinspection PyClassHasNoInit
class TransactionResultCode:
    SUCCESS = 'tx_success'
    FAILED = 'tx_failed'
    TOO_EARLY = 'tx_too_early'
    TOO_LATE = 'tx_too_late'
    MISSING_OPERATION = 'tx_missing_operation'
    BAD_SEQUENCE = 'tx_bad_seq'
    BAD_AUTH = 'tx_bad_auth'
    INSUFFICIENT_BALANCE = 'tx_insufficient_balance'
    NO_ACCOUNT = 'tx_no_source_account'
    INSUFFICIENT_FEE = 'tx_insufficient_fee'
    BAD_AUTH_EXTRA = 'tx_bad_auth_extra'
    INTERNAL_ERROR = 'tx_internal_error'


# noinspection PyClassHasNoInit
class OperationResultCode:
    INNER = 'op_inner'
    BAD_AUTH = 'op_bad_auth'
    NO_ACCOUNT = 'op_no_source_account'


# noinspection PyClassHasNoInit
class CreateAccountResultCode:
    SUCCESS = 'op_success'
    MALFORMED = 'op_malformed'
    UNDERFUNDED = 'op_underfunded'
    LOW_RESERVE = 'op_low_reserve'
    ACCOUNT_EXISTS = 'op_already_exists'


# noinspection PyClassHasNoInit
class PaymentResultCode:
    SUCCESS = 'op_success'
    MALFORMED = 'op_malformed'
    UNDERFUNDED = 'op_underfunded'
    SRC_NO_TRUST = 'op_src_no_trust'
    SRC_NOT_AUTHORIZED = 'op_src_not_authorized'
    NO_DESTINATION = 'op_no_destination'
    NO_TRUST = 'op_no_trust'
    NOT_AUTHORIZED = 'op_not_authorized'
    LINE_FULL = 'op_line_full'
    NO_ISSUER = 'op_no_issuer'


# noinspection PyClassHasNoInit
class PathPaymentResultCode(PaymentResultCode):
    TOO_FEW_OFFERS = 'op_too_few_offers'
    OFFER_CROSS_SELF = 'op_cross_self'
    OVER_SOURCE_MAX = 'op_over_source_max'


# noinspection PyClassHasNoInit
class ManageOfferResultCode:
    SUCCESS = 'op_success'
    MALFORMED = 'op_malformed'
    UNDERFUNDED = 'op_underfunded'
    LINE_FULL = 'op_line_full'
    SELL_NO_TRUST = 'op_sell_no_trust'
    BUY_NO_TRUST = 'op_buy_no_trust'
    SELL_NOT_AUTHORIZED = 'sell_not_authorized'
    BUY_NOT_AUTHORIZED = 'buy_not_authorized'
    OFFER_CROSS_SELF = 'op_cross_self'
    SELL_NO_ISSUER = 'op_sell_no_issuer'
    BUY_NO_ISSUER = 'op_buy_no_issuer'
    OFFER_NOT_FOUND = 'op_offer_not_found'
    OFFER_LOW_RESERVE = 'OpLowReserve'


# noinspection PyClassHasNoInit
class SetOptionsResultCode:
    SUCCESS = 'op_success'
    LOW_RESERVE = 'op_low_reserve'
    TOO_MANY_SIGNERS = 'op_too_many_signers'
    BAD_FLAGS = 'op_bad_flags'
    INVALID_INFLATION = 'op_invalid_inflation'
    CANT_CHANGE = 'op_cant_change'
    UNKNOWN_FLAG = 'op_unknown_flag'
    THRESHOLD_OUT_OF_RANGE = 'op_threshold_out_of_range'
    BAD_SIGNER = 'op_bad_signer'
    INVALID_HOME_DOMAIN = 'op_invalid_home_domain'


# noinspection PyClassHasNoInit
class ChangeTrustResultCode:
    SUCCESS = 'op_success'
    MALFORMED = 'op_malformed'
    NO_ISSUER = 'op_no_issuer'
    LOW_RESERVE = 'op_low_reserve'
    INVALID_LIMIT = 'op_invalid_limit'


# noinspection PyClassHasNoInit
class AllowTrustResultCode:
    SUCCESS = 'op_success'
    MALFORMED = 'op_malformed'
    NO_TRUST_LINE = 'op_no_trustline'
    NOT_REQUIRED = 'op_not_required'
    CANT_REVOKE = 'op_cant_revoke'


# noinspection PyClassHasNoInit
class AccountMergeResultCode:
    SUCCESS = 'op_success'
    MALFORMED = 'op_malformed'
    NO_ACCOUNT = 'op_no_account'
    IMMUTABLE_SET = 'op_immutable_set'
    HAS_SUB_ENTRIES = 'op_has_sub_entries'


# noinspection PyClassHasNoInit
class InflationResultCode:
    SUCCESS = 'op_success'
    NOT_TIME = 'op_not_time'
