"""Contains errors types related to horizon"""

from .horizon_models import HTTPProblemDetails


class ChannelsBusyError(Exception):
    pass


class ChannelsFullError(Exception):
    pass


HORIZON_NS_PREFIX = 'https://stellar.org/horizon-errors/'

'''
Horizon error example:

{
    'status': 400,
    'title': 'Transaction Failed',
    'detail': 'The transaction failed when submitted to the stellar network. The `extras.result_codes` field on this '
              'response contains further details.  Descriptions of each code can be found at: '
              'https://www.stellar.org/developers/learn/concepts/list-of-operations.html',
    'instance': '903d29404b0e/DAurVuBoL4-004368',
    'extras': 	{
        'result_codes': {
            'operations': ['op_no_destination'],
            'transaction': 'tx_failed'
        }, 
        'envelope_xdr': u'AAAAAJgXswhWU+pdHmHIurQuHk4ziNlKFxEJltbMOpF6EqETAAAAZAAAed0AAAAQAAAAAAAAAAAAAAABAAAAAAAAA'
                        u'AEAAAAAxbIcFBPzPZbzjWdkSB5FCSIva+WdQ2Oi70GUmFvFmOcAAAABVEVTVAAAAAD284i665ald1Kiq064FGlL+'
                        u'Aeych/b9UQngBHR37ZeiwAAAAAF9eEAAAAAAAAAAAF6EqETAAAAQN5x3xaOaeDS5EF3tE0X9zXymhqkOg95Tyfgu'
                        u'//TCbv9XN49CHoH5K+BUH04o1ZAZdHbnBABxh44bu7zbFLgQQU=',
        'invalid_field': None,
        'result_xdr': u'AAAAAAAAAGT/////AAAAAQAAAAAAAAAB////+wAAAAA='
    },
    'type': 'https://stellar.org/horizon-errors/transaction_failed'
}
'''


class HorizonError(HTTPProblemDetails, Exception):
    def __init__(self, err_dict):
        super(HTTPProblemDetails, self).__init__(err_dict, strict=False)
        super(Exception, self).__init__(self.title)
        if len(self.type) > len(HORIZON_NS_PREFIX):
            self.type = self.type[len(HORIZON_NS_PREFIX):]


# noinspection PyClassHasNoInit
class HorizonErrorType:
    BAD_REQUEST = 'bad_request'  # cannot understand the request due to invalid parameters
    BEFORE_HISTORY = 'before_history'  # outside the range of recorded history
    FORBIDDEN = 'forbidden'  # not authorized to see
    NOT_ACCEPTABLE = 'not_acceptable'  # cannot reply with the requested data format
    NOT_FOUND = 'not_found'  # resource not found
    NOT_IMPLEMENTED = 'not_implemented'  # request method is not supported
    RATE_LIMIT_EXCEEDED = 'rate_limit_exceeded'  # too many requests in a one hour time frame
    SERVER_OVER_CAPACITY = 'server_over_capacity'  # server is currently overloaded
    STALE_HISTORY = 'stale_history'  # historical request out of date than the configured threshold
    TIMEOUT = 'timeout'  # request timed out before completing
    TRANSACTION_MALFORMED = 'transaction_malformed'
    TRANSACTION_FAILED = 'transaction_failed'  # transaction well-formed but failed
    UNSUPPORTED_MEDIA_TYPE = 'unsupported_media_type'  # unsupported content type
    INTERNAL_SERVER_ERROR = 'server_error'


# references:
# - github.com/stellar/go/blob/master/xdr/xdr_generated.go
# - github.com/stellar/go/blob/master/services/horizon/internal/actions_transaction.go
# - github.com/stellar/go/blob/master/services/horizon/internal/render/problem/main.go
# - github.com/stellar/horizon/blob/master/src/github.com/stellar/horizon/codes/main.go

# noinspection PyClassHasNoInit
class TransactionResultCode:
    SUCCESS = 'tx_success'  # all operations succeeded
    FAILED = 'tx_failed'  # one of the operations failed (none were applied)
    TOO_EARLY = 'tx_too_early'  # ledger closeTime before minTime
    TOO_LATE = 'tx_too_late'  # ledger closeTime after maxTime
    MISSING_OPERATION = 'tx_missing_operation'  # no operation was specified
    BAD_SEQUENCE = 'tx_bad_seq'  # sequence number does not match source account
    BAD_AUTH = 'tx_bad_auth'  # too few valid signatures / wrong network
    INSUFFICIENT_BALANCE = 'tx_insufficient_balance'  # fee would bring account below reserve
    NO_ACCOUNT = 'tx_no_source_account'  # source account not found
    INSUFFICIENT_FEE = 'tx_insufficient_fee'  # fee is too small
    BAD_AUTH_EXTRA = 'tx_bad_auth_extra'  # unused signatures attached to transaction
    INTERNAL_ERROR = 'tx_internal_error'  # an unknown error occurred


# noinspection PyClassHasNoInit
class OperationResultCode:
    INNER = 'op_inner'
    BAD_AUTH = 'op_bad_auth'
    NO_ACCOUNT = 'op_no_source_account'
    NOT_SUPPORTED = 'op_not_supported'


# noinspection PyClassHasNoInit
class CreateAccountResultCode:
    SUCCESS = 'op_success'  # account was created
    MALFORMED = 'op_malformed'  # invalid destination account
    UNDERFUNDED = 'op_underfunded'  # not enough funds in source account
    LOW_RESERVE = 'op_low_reserve'  # would create an account below the min reserve
    ACCOUNT_EXISTS = 'op_already_exists'  # account already exists


# noinspection PyClassHasNoInit
class PaymentResultCode:
    SUCCESS = 'op_success'  # payment successfully completed
    MALFORMED = 'op_malformed'  # bad input
    UNDERFUNDED = 'op_underfunded'  # not enough funds in source account
    SRC_NO_TRUST = 'op_src_no_trust'  # no trust line on source account
    SRC_NOT_AUTHORIZED = 'op_src_not_authorized'  # source not authorized to transfer
    NO_DESTINATION = 'op_no_destination'  # destination account does not exist
    NO_TRUST = 'op_no_trust'  # destination missing a trust line for asset
    NOT_AUTHORIZED = 'op_not_authorized'  # destination not authorized to hold asset
    LINE_FULL = 'op_line_full'  # destination would go above their limit
    NO_ISSUER = 'op_no_issuer'  # missing issuer on asset


# noinspection PyClassHasNoInit
class PathPaymentResultCode(PaymentResultCode):
    TOO_FEW_OFFERS = 'op_too_few_offers'  # not enough offers to satisfy path
    OFFER_CROSS_SELF = 'op_cross_self'  # would cross one of its own offers
    OVER_SOURCE_MAX = 'op_over_source_max'  # could not satisfy sendmax


# noinspection PyClassHasNoInit
class ManageOfferResultCode:
    SUCCESS = 'op_success'  # operation successful
    MALFORMED = 'op_malformed'  # generated offer would be invalid
    UNDERFUNDED = 'op_underfunded'  # doesn't hold what it's trying to sell
    LINE_FULL = 'op_line_full'  # can't receive more of what it's buying
    SELL_NO_TRUST = 'op_sell_no_trust'  # no trust line for what we're selling
    BUY_NO_TRUST = 'op_buy_no_trust'  # no trust line for what we're buying
    SELL_NOT_AUTHORIZED = 'sell_not_authorized'  # not authorized to sell
    BUY_NOT_AUTHORIZED = 'buy_not_authorized'  # not authorized to buy
    OFFER_CROSS_SELF = 'op_cross_self'  # would cross an offer from the same user
    SELL_NO_ISSUER = 'op_sell_no_issuer'  # no issuer for what we're selling
    BUY_NO_ISSUER = 'op_buy_no_issuer'  # no issuer for what we're buying
    OFFER_NOT_FOUND = 'op_offer_not_found'  # offerID does not match an existing offer
    OFFER_LOW_RESERVE = 'op_low_reserve'  # not enough funds to create a new Offer


# noinspection PyClassHasNoInit
class SetOptionsResultCode:
    SUCCESS = 'op_success'  # operation successful
    LOW_RESERVE = 'op_low_reserve'  # not enough funds to add a signer
    TOO_MANY_SIGNERS = 'op_too_many_signers'  # max number of signers already reached
    BAD_FLAGS = 'op_bad_flags'  # invalid combination of clear/set flags
    INVALID_INFLATION = 'op_invalid_inflation'  # inflation account does not exist
    CANT_CHANGE = 'op_cant_change'  # can no longer change this option
    UNKNOWN_FLAG = 'op_unknown_flag'  # can't set an unknown flag
    THRESHOLD_OUT_OF_RANGE = 'op_threshold_out_of_range'  # bad value for weight/threshold
    BAD_SIGNER = 'op_bad_signer'  # signer cannot be masterkey
    INVALID_HOME_DOMAIN = 'op_invalid_home_domain'  # malformed home domain


# noinspection PyClassHasNoInit
class ChangeTrustResultCode:
    SUCCESS = 'op_success'  # operation successful
    MALFORMED = 'op_malformed'  # bad input
    NO_ISSUER = 'op_no_issuer'  # could not find issuer
    LOW_RESERVE = 'op_low_reserve'  # not enough funds to create a new trust line
    INVALID_LIMIT = 'op_invalid_limit'  # cannot drop limit below balance, cannot create with a limit of 0


# noinspection PyClassHasNoInit
class AllowTrustResultCode:
    SUCCESS = 'op_success'  # operation successful
    MALFORMED = 'op_malformed'  # asset is not ASSET_TYPE_ALPHANUM
    NO_TRUST_LINE = 'op_no_trustline'  # trustor does not have a trustline
    NOT_REQUIRED = 'op_not_required'  # source account does not require trust
    CANT_REVOKE = 'op_cant_revoke'  # source account can't revoke trust


# noinspection PyClassHasNoInit
class AccountMergeResultCode:
    SUCCESS = 'op_success'  # operation successful
    MALFORMED = 'op_malformed'  # can't merge onto itself
    NO_ACCOUNT = 'op_no_account'  # destination does not exist
    IMMUTABLE_SET = 'op_immutable_set'  # source account has AUTH_IMMUTABLE set
    HAS_SUB_ENTRIES = 'op_has_sub_entries'  # account has trust lines/offers


# noinspection PyClassHasNoInit
class InflationResultCode:
    SUCCESS = 'op_success'
    NOT_TIME = 'op_not_time'
