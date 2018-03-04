# -*- coding: utf-8 -*

# Copyright (C) 2018 Kin Foundation

from requests.exceptions import ConnectionError as reqConnectionError, RequestException as reqRequestException

from stellar.errors import *


# All exceptions should subclass from SdkError in this module.
class SdkError(Exception):
    """Base class for all SDK errors."""


class SdkConfigurationError(SdkError):
    """Configuration error during SDK initialization"""


class SdkNotConfiguredError(SdkError):
    """Runtime configuration error"""


class ConnectionError(SdkError):
    pass


class RequestError(SdkError):
    pass


class RateLimitError(SdkError):
    pass


class ResourceMissingError(SdkError):
    pass


class NoSuchAccountError(SdkError):
    pass


class AccountExistsError(SdkError):
    pass


class AccountNotActivatedError(SdkError):
    pass


class NoSuchTransactionError(SdkError):
    pass

#class PaymentError(SdkError):
#    pass


class InsufficientNativeBalanceError(SdkError):
    pass


class InsufficientKinBalanceError(SdkError):
    pass


class InternalError(SdkError):
    pass


class TransactionError(SdkError):
    def __init__(self, horizon_error):
        super(TransactionError, self).__init__()
        self.result_code = None
        self.inner_result_codes = None
        if horizon_error.extras and horizon_error.extras.result_codes:
            self.result_code = horizon_error.extras.result_codes.transaction
            if horizon_error.extras.result_codes.operations:
                self.inner_result_codes = horizon_error.extras.result_codes.operations


def translate_error(error):
    if error is reqConnectionError:
        return ConnectionError
    if error is reqRequestException:
        return RequestError
    if error is HorizonError:
        return translate_horizon_error(error)
    return error


horizon_ns_prefix = 'https://stellar.org/horizon-errors/'

# reference: https://github.com/stellar/go/blob/master/services/horizon/internal/render/problem/main.go


def translate_horizon_error(horizon_error):
    err_type = horizon_error[len(horizon_ns_prefix):]
    if horizon_error.status == 400:
        if err_type == 'transaction_failed':
            return TransactionError(horizon_error)
        return RequestError
    if horizon_error.status == 403 or horizon_error.status == 406:
        return RequestError
    if horizon_error.status == 404:  # also not implemented
        return ResourceMissingError
    if horizon_error.status == 429:
        return RateLimitError
    if horizon_error.status == 500 or horizon_error.status == 503:
        return InternalError
    return horizon_error  # TODO
