"""Contains errors related to the Kin SDK"""

from requests.exceptions import RequestException

from .blockchain.errors import *
from kin_base.exceptions import NotValidParamError, StellarAddressInvalidError, StellarSecretInvalidError


# All exceptions should subclass from SdkError in this module.
class SdkError(Exception):
    """Base class for all SDK errors."""

    def __init__(self, message=None, error_code=None, extra=None):
        super(SdkError, self).__init__(self)
        self.message = message or 'unknown error'
        self.error_code = error_code
        self.extra = dict(extra or ())

    def __str__(self):
        sb = list()
        sb.append("\n\tmessage='{}'".format(self.message))
        sb.append("\n\terror_code='{}'".format(self.error_code))
        sb.append("\n\textra data:")
        for key in self.extra:
            sb.append("\n\t\t{}='{}'".format(key, self.extra[key]))
        return ''.join(sb)


class ThrottleError(SdkError):
    """Service is busy"""

    def __init__(self):
        super(ThrottleError, self).__init__('service is busy, retry later')


class NetworkError(SdkError):
    """Network-level errors - connection error, timeout error, etc."""

    def __init__(self, extra=None):
        super(NetworkError, self).__init__('network error', None, extra)


class RequestError(SdkError):
    """Request-related errors - bad request, invalid payload, malformed transaction, etc."""

    def __init__(self, error_code=None, extra=None):
        super(RequestError, self).__init__('bad request', error_code, extra)


class ServerError(SdkError):
    """Server-related errors - rate limit exceeded, server over capacity."""

    def __init__(self, error_code=None, extra=None):
        super(ServerError, self).__init__('server error', error_code, extra)


class ResourceNotFoundError(SdkError):
    """Resource not found on the server."""

    def __init__(self, error_code=None, extra=None):
        super(ResourceNotFoundError, self).__init__('resource not found', error_code, extra)


class AccountError(SdkError):
    """Base class for account-related errors."""

    def __init__(self, address=None, message=None, error_code=None, extra=None):
        if address:
            extra = dict(extra or ())
            extra.update({'account': address})
        super(AccountError, self).__init__(message, error_code, extra)


class AccountNotFoundError(AccountError):
    """Operation referenced a nonexistent account."""

    def __init__(self, address=None, error_code=None, extra=None):
        super(AccountNotFoundError, self).__init__(address, 'account not found', error_code, extra)


class AccountActivatedError(AccountError):
    """Trying to activate an activated account."""

    def __init__(self, address=None, error_code=None, extra=None):
        super(AccountActivatedError, self).__init__(address, 'account already activated', error_code, extra)


class AccountExistsError(AccountError):
    """Trying to create an existing account."""

    def __init__(self, address=None, error_code=None, extra=None):
        super(AccountExistsError, self).__init__(address, 'account already exists', error_code, extra)


class AccountNotActivatedError(AccountError):
    """Operation referenced an account that exists but not yet activated."""

    def __init__(self, address=None, error_code=None, extra=None):
        super(AccountNotActivatedError, self).__init__(address, 'account not activated', error_code, extra)


class LowBalanceError(SdkError):
    """Account balance is too low to complete the operation. Refers both to native and asset balance."""

    def __init__(self, error_code=None, extra=None):
        super(LowBalanceError, self).__init__('low balance', error_code, extra)


class InternalError(SdkError):
    """Internal unhandled error. To find out more, check the error code and extra data."""

    def __init__(self, error_code=None, extra=None):
        super(InternalError, self).__init__('internal error', error_code, extra)


class FriendbotError(SdkError):
    """Friendbot related error"""

    def __init__(self, error_code=None, extra=None):
        super(FriendbotError, self).__init__('friendbot error', error_code, extra)


class CantSimplifyError(SdkError):
    """Transaction is too complex to simplify"""

    def __init__(self, error_code=None, extra=None):
        super(CantSimplifyError, self).__init__('Tx simplification error', error_code, extra)


class StoppedMonitorError(SdkError):
    """A stopped monitor cannot be modified"""

    def __init__(self, error_code=None, extra=None):
        super(StoppedMonitorError, self).__init__('Stopped monitor cannot be modified', error_code, extra)


class WrongNetworkError(SdkError):
    """The account is not using the network specified in the tx"""

    def __init__(self, error_code=None, extra=None):
        super(WrongNetworkError, self).__init__('The account is not using the network specified in the transaction',
                                                error_code, extra)


def translate_error(err):
    """A high-level error translator."""
    if isinstance(err, RequestException):
        return NetworkError({'internal_error': str(err)})
    if isinstance(err, ChannelsBusyError):
        return ThrottleError
    if isinstance(err, HorizonError):
        return translate_horizon_error(err)
    return InternalError(None, {'internal_error': str(err)})


def translate_horizon_error(horizon_error):
    """Horizon error translator."""
    # query errors
    if horizon_error.type == HorizonErrorType.BAD_REQUEST:
        return RequestError(horizon_error.type, {'invalid_field': horizon_error.extras.invalid_field})
    if horizon_error.type == HorizonErrorType.NOT_FOUND:
        return ResourceNotFoundError(horizon_error.type)
    if horizon_error.type in [HorizonErrorType.FORBIDDEN,
                              HorizonErrorType.NOT_ACCEPTABLE,
                              HorizonErrorType.UNSUPPORTED_MEDIA_TYPE,
                              HorizonErrorType.NOT_IMPLEMENTED,
                              HorizonErrorType.BEFORE_HISTORY,
                              HorizonErrorType.STALE_HISTORY]:
        return RequestError(horizon_error.type)

    # transaction (submit) errors
    if horizon_error.type == HorizonErrorType.TRANSACTION_MALFORMED:
        return RequestError(horizon_error.type)
    if horizon_error.type == HorizonErrorType.TRANSACTION_FAILED:
        return translate_transaction_error(horizon_error)

    # server errors
    if horizon_error.type == HorizonErrorType.RATE_LIMIT_EXCEEDED \
            or horizon_error.type == HorizonErrorType.SERVER_OVER_CAPACITY \
            or horizon_error.type == HorizonErrorType.TIMEOUT:
        return ServerError(horizon_error.type)
    if horizon_error.type == HorizonErrorType.INTERNAL_SERVER_ERROR:
        return InternalError(horizon_error.type)

    # unknown
    return InternalError(horizon_error.type, {'internal_error': 'unknown horizon error'})


def translate_transaction_error(tx_error):
    """Transaction error translator."""
    tx_result_code = tx_error.extras.result_codes.transaction
    if tx_result_code in [TransactionResultCode.TOO_EARLY,
                          TransactionResultCode.TOO_LATE,
                          TransactionResultCode.MISSING_OPERATION,
                          TransactionResultCode.BAD_AUTH,
                          TransactionResultCode.BAD_AUTH_EXTRA,
                          TransactionResultCode.BAD_SEQUENCE,
                          TransactionResultCode.INSUFFICIENT_FEE]:
        return RequestError(tx_result_code)
    if tx_result_code == TransactionResultCode.NO_ACCOUNT:
        return AccountNotFoundError(error_code=tx_result_code)
    if tx_result_code == TransactionResultCode.INSUFFICIENT_BALANCE:
        return LowBalanceError(tx_result_code)
    if tx_result_code == TransactionResultCode.FAILED:
        return translate_operation_error(tx_error.extras.result_codes.operations)
    return InternalError(tx_result_code, {'internal_error': 'unknown transaction error'})


def translate_operation_error(op_result_codes):
    """Operation error translator."""
    # NOTE: we currently handle only one operation per transaction!
    op_result_code = op_result_codes[0]
    if op_result_code == OperationResultCode.BAD_AUTH \
            or op_result_code == CreateAccountResultCode.MALFORMED \
            or op_result_code == PaymentResultCode.NO_ISSUER \
            or op_result_code == PaymentResultCode.LINE_FULL \
            or op_result_code == ChangeTrustResultCode.INVALID_LIMIT:
        return RequestError(op_result_code)
    if op_result_code == OperationResultCode.NO_ACCOUNT or op_result_code == PaymentResultCode.NO_DESTINATION:
        return AccountNotFoundError(error_code=op_result_code)
    if op_result_code == CreateAccountResultCode.ACCOUNT_EXISTS:
        return AccountExistsError(error_code=op_result_code)
    if op_result_code == CreateAccountResultCode.LOW_RESERVE \
            or op_result_code == PaymentResultCode.UNDERFUNDED:
        return LowBalanceError(op_result_code)
    if op_result_code == PaymentResultCode.SRC_NO_TRUST \
            or op_result_code == PaymentResultCode.NO_TRUST \
            or op_result_code == PaymentResultCode.SRC_NOT_AUTHORIZED \
            or op_result_code == PaymentResultCode.NOT_AUTHORIZED:
        return AccountNotActivatedError(error_code=op_result_code)
    return InternalError(op_result_code, {'internal_error': 'unknown operation error'})
