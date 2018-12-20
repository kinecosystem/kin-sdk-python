from requests.exceptions import RequestException

from kin import KinErrors
from kin.blockchain.errors import *


def test_sdk_error():
    e = KinErrors.SdkError(message='message', error_code=1, extra={'key': 'value'})
    assert e.message == 'message'
    assert e.error_code == 1
    assert e.extra == {'key': 'value'}
    str(e)  # cover __str__ method


def test_translate_error():
    e = KinErrors.translate_error(RequestException('error'))
    assert isinstance(e, KinErrors.NetworkError)
    assert e.extra['internal_error'] == 'error'

    e = KinErrors.translate_error(Exception('error'))
    assert isinstance(e, KinErrors.InternalError)
    assert e.extra['internal_error'] == 'error'


def test_translate_horizon_error():
    err_dict = dict(title='title', status=400, detail='detail', instance='instance', extras={})

    fixtures = [
        # RequestError
        [HorizonErrorType.BAD_REQUEST, KinErrors.RequestError, 'bad request', {}],
        [HorizonErrorType.FORBIDDEN, KinErrors.RequestError, 'bad request', {}],
        [HorizonErrorType.NOT_ACCEPTABLE, KinErrors.RequestError, 'bad request', {}],
        [HorizonErrorType.UNSUPPORTED_MEDIA_TYPE, KinErrors.RequestError, 'bad request', {}],
        [HorizonErrorType.NOT_IMPLEMENTED, KinErrors.RequestError, 'bad request', {}],
        [HorizonErrorType.BEFORE_HISTORY, KinErrors.RequestError, 'bad request', {}],
        [HorizonErrorType.STALE_HISTORY, KinErrors.RequestError, 'bad request', {}],
        [HorizonErrorType.TRANSACTION_MALFORMED, KinErrors.RequestError, 'bad request', {}],

        # ResourceNotFoundError
        [HorizonErrorType.NOT_FOUND, KinErrors.ResourceNotFoundError, 'resource not found', {}],

        # ServerError
        [HorizonErrorType.RATE_LIMIT_EXCEEDED, KinErrors.ServerError, 'server error', {}],
        [HorizonErrorType.SERVER_OVER_CAPACITY, KinErrors.ServerError, 'server error', {}],

        # InternalError
        [HorizonErrorType.INTERNAL_SERVER_ERROR, KinErrors.InternalError, 'internal error', {}],
        ['unknown', KinErrors.InternalError, 'internal error', {'internal_error': 'unknown horizon error'}],
    ]

    for fixture in fixtures:
        err_dict['type'] = HORIZON_NS_PREFIX + fixture[0]
        e = KinErrors.translate_horizon_error(HorizonError(err_dict))
        assert isinstance(e, fixture[1])
        assert e.error_code == fixture[0]
        assert e.message == fixture[2]


def test_translate_transaction_error():
    err_dict = dict(type=HORIZON_NS_PREFIX + HorizonErrorType.TRANSACTION_FAILED, title='title', status=400,
                    detail='detail', instance='instance',
                    extras={'result_codes': {'operations': [], 'transaction': 'tx_failed'}})

    fixtures = [
        # RequestError
        [TransactionResultCode.TOO_EARLY, KinErrors.RequestError, 'bad request', {}],
        [TransactionResultCode.TOO_LATE, KinErrors.RequestError, 'bad request', {}],
        [TransactionResultCode.MISSING_OPERATION, KinErrors.RequestError, 'bad request', {}],
        [TransactionResultCode.BAD_AUTH, KinErrors.RequestError, 'bad request', {}],
        [TransactionResultCode.BAD_AUTH_EXTRA, KinErrors.RequestError, 'bad request', {}],
        [TransactionResultCode.BAD_SEQUENCE, KinErrors.RequestError, 'bad request', {}],
        [TransactionResultCode.INSUFFICIENT_FEE, KinErrors.RequestError, 'bad request', {}],

        # AccountNotFoundError
        [TransactionResultCode.NO_ACCOUNT, KinErrors.AccountNotFoundError, 'account not found', {}],

        # LowBalanceError
        [TransactionResultCode.INSUFFICIENT_BALANCE, KinErrors.LowBalanceError, 'low balance', {}],

        # InternalError
        ['unknown', KinErrors.InternalError, 'internal error', {'internal_error': 'unknown transaction error'}]
    ]

    for fixture in fixtures:
        err_dict['extras']['result_codes']['transaction'] = fixture[0]
        e = KinErrors.translate_horizon_error(HorizonError(err_dict))
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
        [[OperationResultCode.BAD_AUTH], KinErrors.RequestError, 'bad request', {}],
        [[CreateAccountResultCode.MALFORMED], KinErrors.RequestError, 'bad request', {}],
        [[PaymentResultCode.NO_ISSUER], KinErrors.RequestError, 'bad request', {}],
        [[PaymentResultCode.LINE_FULL], KinErrors.RequestError, 'bad request', {}],
        [[ChangeTrustResultCode.INVALID_LIMIT], KinErrors.RequestError, 'bad request', {}],

        # AccountNotFoundError
        [[OperationResultCode.NO_ACCOUNT], KinErrors.AccountNotFoundError, 'account not found', {}],
        [[PaymentResultCode.NO_DESTINATION], KinErrors.AccountNotFoundError, 'account not found', {}],

        # AccountExistsError
        [[CreateAccountResultCode.ACCOUNT_EXISTS], KinErrors.AccountExistsError, 'account already exists', {}],

        # LowBalanceError
        [[CreateAccountResultCode.LOW_RESERVE], KinErrors.LowBalanceError, 'low balance', {}],
        [[PaymentResultCode.UNDERFUNDED], KinErrors.LowBalanceError, 'low balance', {}],

        # AccountNotActivatedError
        [[PaymentResultCode.SRC_NO_TRUST], KinErrors.AccountNotActivatedError, 'account not activated', {}],
        [[PaymentResultCode.NO_TRUST], KinErrors.AccountNotActivatedError, 'account not activated', {}],
        [[PaymentResultCode.SRC_NOT_AUTHORIZED], KinErrors.AccountNotActivatedError, 'account not activated', {}],
        [[PaymentResultCode.NOT_AUTHORIZED], KinErrors.AccountNotActivatedError, 'account not activated', {}],

        # InternalError
        [['unknown'], KinErrors.InternalError, 'internal error', {'internal_error': 'unknown operation error'}],

        # MultiOp
        [[OperationResultCode.SUCCESS, PaymentResultCode.UNDERFUNDED], KinErrors.LowBalanceError, 'low balance', {}]
    ]

    for fixture in fixtures:
        err_dict['extras']['result_codes']['operations'] = fixture[0]
        e = KinErrors.translate_horizon_error(HorizonError(err_dict))
        assert isinstance(e, fixture[1])
        assert e.error_code == fixture[0][-1]
        assert e.message == fixture[2]
        assert e.extra == fixture[3]
