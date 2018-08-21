from requests.exceptions import RequestException

import kin
from kin.errors import translate_error, translate_horizon_error
from kin.blockchain.errors import *


def test_sdk_error():
    e = kin.SdkError(message='message', error_code=1, extra={'key': 'value'})
    assert e.message == 'message'
    assert e.error_code == 1
    assert e.extra == {'key': 'value'}
    str(e)  # cover __str__ method


def test_translate_error():
    e = translate_error(RequestException('error'))
    assert isinstance(e, kin.NetworkError)
    assert e.extra['internal_error'] == 'error'

    e = translate_error(Exception('error'))
    assert isinstance(e, kin.InternalError)
    assert e.extra['internal_error'] == 'error'


def test_translate_horizon_error():
    err_dict = dict(title='title', status=400, detail='detail', instance='instance', extras={})

    fixtures = [
        # RequestError
        [HorizonErrorType.BAD_REQUEST, kin.RequestError, 'bad request', {}],
        [HorizonErrorType.FORBIDDEN, kin.RequestError, 'bad request', {}],
        [HorizonErrorType.NOT_ACCEPTABLE, kin.RequestError, 'bad request', {}],
        [HorizonErrorType.UNSUPPORTED_MEDIA_TYPE, kin.RequestError, 'bad request', {}],
        [HorizonErrorType.NOT_IMPLEMENTED, kin.RequestError, 'bad request', {}],
        [HorizonErrorType.BEFORE_HISTORY, kin.RequestError, 'bad request', {}],
        [HorizonErrorType.STALE_HISTORY, kin.RequestError, 'bad request', {}],
        [HorizonErrorType.TRANSACTION_MALFORMED, kin.RequestError, 'bad request', {}],

        # ResourceNotFoundError
        [HorizonErrorType.NOT_FOUND, kin.ResourceNotFoundError, 'resource not found', {}],

        # ServerError
        [HorizonErrorType.RATE_LIMIT_EXCEEDED, kin.ServerError, 'server error', {}],
        [HorizonErrorType.SERVER_OVER_CAPACITY, kin.ServerError, 'server error', {}],

        # InternalError
        [HorizonErrorType.INTERNAL_SERVER_ERROR, kin.InternalError, 'internal error', {}],
        ['unknown', kin.InternalError, 'internal error', {'internal_error': 'unknown horizon error'}],
    ]

    for fixture in fixtures:
        err_dict['type'] = HORIZON_NS_PREFIX + fixture[0]
        e = translate_horizon_error(HorizonError(err_dict))
        assert isinstance(e, fixture[1])
        assert e.error_code == fixture[0]
        assert e.message == fixture[2]


def test_translate_transaction_error():
    err_dict = dict(type=HORIZON_NS_PREFIX + HorizonErrorType.TRANSACTION_FAILED, title='title', status=400,
                    detail='detail', instance='instance',
                    extras={'result_codes': {'operations': [], 'transaction': 'tx_failed'}})

    fixtures = [
        # RequestError
        [TransactionResultCode.TOO_EARLY, kin.RequestError, 'bad request', {}],
        [TransactionResultCode.TOO_LATE, kin.RequestError, 'bad request', {}],
        [TransactionResultCode.MISSING_OPERATION, kin.RequestError, 'bad request', {}],
        [TransactionResultCode.BAD_AUTH, kin.RequestError, 'bad request', {}],
        [TransactionResultCode.BAD_AUTH_EXTRA, kin.RequestError, 'bad request', {}],
        [TransactionResultCode.BAD_SEQUENCE, kin.RequestError, 'bad request', {}],
        [TransactionResultCode.INSUFFICIENT_FEE, kin.RequestError, 'bad request', {}],

        # AccountNotFoundError
        [TransactionResultCode.NO_ACCOUNT, kin.AccountNotFoundError, 'account not found', {}],

        # LowBalanceError
        [TransactionResultCode.INSUFFICIENT_BALANCE, kin.LowBalanceError, 'low balance', {}],

        # InternalError
        ['unknown', kin.InternalError, 'internal error', {'internal_error': 'unknown transaction error'}]
    ]

    for fixture in fixtures:
        err_dict['extras']['result_codes']['transaction'] = fixture[0]
        e = translate_horizon_error(HorizonError(err_dict))
        assert isinstance(e, fixture[1])
        assert e.error_code == fixture[0]
        assert e.message == fixture[2]
        assert e.extra == fixture[3]


def test_translate_operation_error():
    # RequestError
    err_dict = dict(type=HORIZON_NS_PREFIX + HorizonErrorType.TRANSACTION_FAILED, title='title', status=400,
                    detail='detail', instance='instance',
                    extras={'result_codes': {'operations': [], 'transaction': 'tx_failed'}})

    fixtures = [
        # RequestError
        [OperationResultCode.BAD_AUTH, kin.RequestError, 'bad request', {}],
        [CreateAccountResultCode.MALFORMED, kin.RequestError, 'bad request', {}],
        [PaymentResultCode.NO_ISSUER, kin.RequestError, 'bad request', {}],
        [PaymentResultCode.LINE_FULL, kin.RequestError, 'bad request', {}],
        [ChangeTrustResultCode.INVALID_LIMIT, kin.RequestError, 'bad request', {}],

        # AccountNotFoundError
        [OperationResultCode.NO_ACCOUNT, kin.AccountNotFoundError, 'account not found', {}],
        [PaymentResultCode.NO_DESTINATION, kin.AccountNotFoundError, 'account not found', {}],

        # AccountExistsError
        [CreateAccountResultCode.ACCOUNT_EXISTS, kin.AccountExistsError, 'account already exists', {}],

        # LowBalanceError
        [CreateAccountResultCode.LOW_RESERVE, kin.LowBalanceError, 'low balance', {}],
        [PaymentResultCode.UNDERFUNDED, kin.LowBalanceError, 'low balance', {}],

        # AccountNotActivatedError
        [PaymentResultCode.SRC_NO_TRUST, kin.AccountNotActivatedError, 'account not activated', {}],
        [PaymentResultCode.NO_TRUST, kin.AccountNotActivatedError, 'account not activated', {}],
        [PaymentResultCode.SRC_NOT_AUTHORIZED, kin.AccountNotActivatedError, 'account not activated', {}],
        [PaymentResultCode.NOT_AUTHORIZED, kin.AccountNotActivatedError, 'account not activated', {}],

        # InternalError
        ['unknown', kin.InternalError, 'internal error', {'internal_error': 'unknown operation error'}]
    ]

    for fixture in fixtures:
        err_dict['extras']['result_codes']['operations'] = [fixture[0]]
        e = translate_horizon_error(HorizonError(err_dict))
        assert isinstance(e, fixture[1])
        assert e.error_code == fixture[0]
        assert e.message == fixture[2]
        assert e.extra == fixture[3]

