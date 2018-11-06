import pytest
from requests.adapters import DEFAULT_POOLSIZE

from kin_base.horizon import HORIZON_TEST, HORIZON_LIVE
from kin.blockchain.errors import *
from kin.blockchain.horizon import (
    Horizon,
    check_horizon_reply,
    DEFAULT_REQUEST_TIMEOUT,
    DEFAULT_NUM_RETRIES,
    DEFAULT_BACKOFF_FACTOR,
    USER_AGENT,
)


def test_check_horizon_reply():
    reply = {
        'type': HORIZON_NS_PREFIX + HorizonErrorType.TRANSACTION_FAILED,
        'status': 400,
        'title': 'title',
        'extras': {
            'result_codes': {
                'operations': [PaymentResultCode.NO_TRUST],
                'transaction': TransactionResultCode.FAILED
            }
        }
    }
    with pytest.raises(HorizonError) as exc_info:
        check_horizon_reply(reply)
    assert exc_info.value.type == HorizonErrorType.TRANSACTION_FAILED

    reply = "{'a':'b'}"
    check_horizon_reply(reply)


def test_defaults():
    horizon = Horizon.testnet()
    assert horizon
    assert horizon.horizon_uri == HORIZON_TEST

    horizon = Horizon.livenet()
    assert horizon
    assert horizon.horizon_uri == HORIZON_LIVE


def test_create_default():
    horizon = Horizon()
    assert horizon
    assert horizon.horizon_uri == HORIZON_TEST
    assert horizon.request_timeout == DEFAULT_REQUEST_TIMEOUT
    assert horizon._session
    assert horizon._session.headers['User-Agent'] == USER_AGENT
    assert horizon._session.adapters['http://']
    assert horizon._session.adapters['https://']
    adapter = horizon._session.adapters['http://']
    assert adapter.max_retries
    assert adapter.max_retries.total == DEFAULT_NUM_RETRIES
    assert adapter.max_retries.backoff_factor == DEFAULT_BACKOFF_FACTOR
    assert adapter.max_retries.redirect == 0
    assert adapter._pool_connections == DEFAULT_POOLSIZE
    assert adapter._pool_maxsize == DEFAULT_POOLSIZE


def test_create_custom():
    horizon_uri = 'horizon_uri'
    pool_size = 5
    num_retries = 10
    request_timeout = 30
    backoff_factor = 5
    horizon = Horizon(horizon_uri=horizon_uri, pool_size=pool_size, num_retries=num_retries,
                      request_timeout=request_timeout, backoff_factor=backoff_factor)
    assert horizon
    assert horizon.horizon_uri == horizon_uri
    assert horizon.request_timeout == request_timeout
    assert horizon._session.headers['User-Agent'] == USER_AGENT
    adapter = horizon._session.adapters['http://']
    assert adapter.max_retries.total == num_retries
    assert adapter.max_retries.backoff_factor == backoff_factor
    assert adapter.max_retries.redirect == 0
    assert adapter._pool_connections == pool_size
    assert adapter._pool_maxsize == pool_size


def test_account(test_client):
    with pytest.raises(HorizonError) as exc_info:
        test_client.horizon.account('bad')
    assert exc_info.value.type == HorizonErrorType.NOT_FOUND

    # root blockchain address
    address = 'GCLBBAIDP34M4JACPQJUYNSPZCQK7IRHV7ETKV6U53JPYYUIIVDVJJFQ'
    reply = test_client.horizon.account(address)
    assert reply
    assert reply['id']


def test_account_effects(test_client, test_account):
    with pytest.raises(HorizonError) as exc_info:
        test_client.horizon.account_effects('bad')
    assert exc_info.value.type == HorizonErrorType.NOT_FOUND

    # root blockchain address
    address = test_account.get_public_address()
    reply = test_client.horizon.account_effects(address)
    assert reply
    assert reply['_embedded']['records']


def test_account_offers(test_client):
    # does not raise on nonexistent account!

    # root blockchain address
    address = 'GCLBBAIDP34M4JACPQJUYNSPZCQK7IRHV7ETKV6U53JPYYUIIVDVJJFQ'
    reply = test_client.horizon.account_offers(address)
    assert reply
    assert reply['_embedded']


def test_account_operations(test_client, test_account):
    with pytest.raises(HorizonError) as exc_info:
        test_client.horizon.account_operations('bad')
    assert exc_info.value.type == HorizonErrorType.NOT_FOUND

    address = test_account.get_public_address()
    reply = test_client.horizon.account_operations(address)
    assert reply
    assert reply['_embedded']['records']


def test_account_transactions(test_client, test_account):
    with pytest.raises(HorizonError) as exc_info:
        test_client.horizon.account_transactions('bad')
    assert exc_info.value.type == HorizonErrorType.NOT_FOUND

    address = test_account.get_public_address()
    reply = test_client.horizon.account_transactions(address)
    assert reply
    assert reply['_embedded']['records']


def test_account_payments(test_client, test_account):
    with pytest.raises(HorizonError) as exc_info:
        test_client.horizon.account_payments('bad')
    assert exc_info.value.type == HorizonErrorType.NOT_FOUND

    address = test_account.get_public_address()
    reply = test_client.horizon.account_payments(address)
    assert reply
    assert reply['_embedded']['records']


def test_transactions(test_client):
    reply = test_client.horizon.transactions()
    assert reply
    assert reply['_embedded']['records']


def get_first_tx_hash(test_client, test_account):
    if not hasattr(test_account, 'first_tx_hash'):
        address = test_account.get_public_address()
        reply = test_client.horizon.account_transactions(address)
        assert reply
        tx = reply['_embedded']['records'][0]
        assert tx['hash']
        test_account.first_tx_hash = tx['hash']
    return test_account.first_tx_hash


def test_transaction(test_client, test_account):
    with pytest.raises(HorizonError) as exc_info:
        test_account.horizon.transaction('bad')
    assert exc_info.value.type == HorizonErrorType.NOT_FOUND

    tx_id = get_first_tx_hash(test_client, test_account)
    reply = test_account.horizon.transaction(tx_id)
    assert reply
    assert reply['id'] == tx_id

    assert reply['operation_count'] == 1


def test_transaction_effects(test_client, test_account):
    with pytest.raises(HorizonError) as exc_info:
        test_client.horizon.transaction_effects('bad')
    assert exc_info.value.type == HorizonErrorType.NOT_FOUND

    tx_id = get_first_tx_hash(test_client, test_account)
    reply = test_client.horizon.transaction_effects(tx_id)
    assert reply
    assert reply['_embedded']['records']


def test_transaction_operations(test_client, test_account):
    with pytest.raises(HorizonError) as exc_info:
        test_client.horizon.transaction_operations('bad')
    assert exc_info.value.type == HorizonErrorType.NOT_FOUND

    tx_id = get_first_tx_hash(test_client, test_account)
    reply = test_client.horizon.transaction_operations(tx_id)
    assert reply
    assert reply['_embedded']['records']


def test_transaction_payments(test_client, test_account):
    with pytest.raises(HorizonError) as exc_info:
        test_client.horizon.transaction_payments('bad')
    assert exc_info.value.type == HorizonErrorType.NOT_FOUND

    tx_id = get_first_tx_hash(test_client, test_account)
    reply = test_client.horizon.transaction_payments(tx_id)
    assert reply
    assert reply['_embedded']['records']


def test_order_book(setup, test_client):
    params = {
        'selling_asset_type': 'credit_alphanum4',
        'selling_asset_code': 'KIN',
        'selling_asset_issuer': setup.issuer_address,
        'buying_asset_type': 'native',
        'buying_asset_code': 'XLM',
    }
    reply = test_client.horizon.order_book(params=params)
    assert reply
    assert reply['base']['asset_code'] == 'KIN'


def test_ledgers(test_client):
    reply = test_client.horizon.ledgers()
    assert reply
    assert reply['_embedded']['records']


def test_ledger(test_client):
    with pytest.raises(HorizonError) as exc_info:
        test_client.horizon.ledger('bad')
    assert exc_info.value.type == HorizonErrorType.BAD_REQUEST  # not 'Resource Missing'!

    reply = test_client.horizon.ledger(5)
    assert reply
    assert reply['sequence'] == 5


def test_ledger_effects(test_client):
    with pytest.raises(HorizonError, match='Bad Request') as exc_info:
        test_client.horizon.ledger_effects('bad')
    assert exc_info.value.type == HorizonErrorType.BAD_REQUEST  # not 'Resource Missing'!

    reply = test_client.horizon.ledger_effects(5)
    assert reply
    assert reply['_embedded']


def test_ledger_operations(test_client):
    with pytest.raises(HorizonError) as exc_info:
        test_client.horizon.ledger_operations('bad')
    assert exc_info.value.type == HorizonErrorType.BAD_REQUEST  # not 'Resource Missing'!

    reply = test_client.horizon.ledger_operations(5)
    assert reply
    assert reply['_embedded']


def test_ledger_payments(test_client):
    with pytest.raises(HorizonError) as exc_info:
        test_client.horizon.ledger_payments('bad')
    assert exc_info.value.type == HorizonErrorType.BAD_REQUEST  # not 'Resource Missing'!

    reply = test_client.horizon.ledger_payments(5)
    assert reply
    assert reply['_embedded']


def test_effects(test_client):
    reply = test_client.horizon.effects()
    assert reply
    assert reply['_embedded']['records']


def test_operations(test_client):
    reply = test_client.horizon.operations()
    assert reply
    assert reply['_embedded']['records']


def test_operation(test_client):
    with pytest.raises(HorizonError) as exc_info:
        test_client.horizon.operation('bad')
    assert exc_info.value.type == HorizonErrorType.BAD_REQUEST  # not 'Resource Missing'!

    reply = test_client.horizon.operations()
    op_id = reply['_embedded']['records'][0]['id']

    reply = test_client.horizon.operation(op_id)
    assert reply
    assert reply['id'] == op_id


def test_operation_effects(test_client):
    with pytest.raises(HorizonError) as exc_info:
        test_client.horizon.operation_effects('bad')
    assert exc_info.value.type == HorizonErrorType.BAD_REQUEST  # not 'Resource Missing'!

    reply = test_client.horizon.operations()
    op_id = reply['_embedded']['records'][0]['id']

    reply = test_client.horizon.operation_effects(op_id)
    assert reply
    assert reply['_embedded']['records']


def test_payments(test_client):
    reply = test_client.horizon.payments()
    assert reply
    assert reply['_embedded']['records']


def test_assets(test_client):
    reply = test_client.horizon.assets()
    assert reply
    assert reply['_embedded']['records']


def test_horizon_error_hashable():
    err_dict = dict(title='title',
                    status=400,
                    detail='detail',
                    instance='instance',
                    extras={},
                    type=HORIZON_NS_PREFIX + HorizonErrorType.BAD_REQUEST)
    e = HorizonError(err_dict)
    {e: 1}  # shouldn't fail on unhashable type
