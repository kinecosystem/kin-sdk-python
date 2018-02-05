import pytest
from requests.adapters import DEFAULT_POOLSIZE
from stellar_base.horizon import HORIZON_TEST, HORIZON_LIVE
from kin.horizon import Horizon, DEFAULT_REQUEST_TIMEOUT, DEFAULT_NUM_RETRIES, DEFAULT_BACKOFF_FACTOR, USER_AGENT


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
    assert adapter._pool_connections == 1
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
    assert adapter._pool_connections == 1
    assert adapter._pool_maxsize == pool_size


def test_account(test_sdk):
    address = test_sdk.get_address()

    reply = test_sdk.horizon.account(address)
    assert reply
    assert reply['id']

    # effects
    reply = test_sdk.horizon.account_effects(address)
    assert reply
    assert reply['_embedded']['records'][0]

    # offers
    reply = test_sdk.horizon.account_offers(address)
    assert reply
    assert reply['_embedded']

    # operations
    reply = test_sdk.horizon.account_operations(address)
    assert reply
    assert reply['_embedded']['records'][0]

    # transactions
    reply = test_sdk.horizon.account_transactions(address)
    assert reply
    assert reply['_embedded']['records'][0]

    # payments
    reply = test_sdk.horizon.account_payments(address)
    assert reply
    assert reply['_embedded']['records'][0]


def test_transaction(test_sdk):
    reply = test_sdk.horizon.transactions(test_sdk.get_address())
    assert reply
    assert reply['_embedded']['records'][0]
    tx_id = reply['_embedded']['records'][0]['id']

    reply = test_sdk.horizon.transaction(tx_id)
    assert reply
    assert reply['id'] == tx_id

    # effects
    reply = test_sdk.horizon.transaction_effects(tx_id)
    assert reply
    assert reply['_embedded']['records'][0]

    # operations
    reply = test_sdk.horizon.transaction_operations(tx_id)
    assert reply
    assert reply['_embedded']['records'][0]

    # payments
    reply = test_sdk.horizon.transaction_payments(tx_id)
    assert reply
    assert reply['_embedded']['records'][0]


def test_order_book(setup, test_sdk):
    params = {
        'selling_asset_type': 'credit_alphanum4',
        'selling_asset_code': setup.test_asset.code,
        'selling_asset_issuer': setup.test_asset.issuer,
        'buying_asset_type': 'native',
        'buying_asset_code': 'XLM',
    }
    reply = test_sdk.horizon.order_book(params=params)
    assert reply
    assert reply['base']['asset_code'] == setup.test_asset.code

    # trades
    params = {
        'base_asset_type': 'credit_alphanum4',
        'base_asset_code': setup.test_asset.code,
        'base_asset_issuer': setup.test_asset.issuer,
        'counter_asset_type': 'native',
        'counter_asset_code': 'XLM',
    }
    reply = test_sdk.horizon.order_book_trades(params=params)
    assert reply['_embedded']


def test_ledger(test_sdk):
    reply = test_sdk.horizon.ledgers()
    assert reply
    assert reply['_embedded']['records'][0]
    ledger_num = reply['_embedded']['records'][0]['sequence']

    reply = test_sdk.horizon.ledger(ledger_num)
    assert reply
    assert reply['sequence'] == ledger_num

    # effects
    reply = test_sdk.horizon.ledger_effects(ledger_num)
    assert reply
    assert reply['_embedded']

    # operations
    reply = test_sdk.horizon.ledger_operations(ledger_num)
    assert reply
    assert reply['_embedded']

    # payments
    reply = test_sdk.horizon.ledger_payments(ledger_num)
    assert reply
    assert reply['_embedded']


def test_effects(test_sdk):
    reply = test_sdk.horizon.effects()
    assert reply
    assert reply['_embedded']['records'][0]


def test_operation(test_sdk):
    reply = test_sdk.horizon.operations()
    assert reply
    assert reply['_embedded']['records'][0]
    op_id = reply['_embedded']['records'][0]['id']

    reply = test_sdk.horizon.operation(op_id)
    assert reply
    assert reply['id'] == op_id

    # effects
    reply = test_sdk.horizon.operation_effects(op_id)
    assert reply
    assert reply['_embedded']['records'][0]


def test_payments(test_sdk):
    reply = test_sdk.horizon.payments()
    assert reply
    assert reply['_embedded']['records'][0]


def test_assets(test_sdk):
    #reply = test_sdk.horizon.assets()
    #assert reply
    #assert reply['_embedded']['records'][0]
    pass
