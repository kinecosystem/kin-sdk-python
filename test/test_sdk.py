from decimal import Decimal
import pytest
import threading
from time import sleep

from stellar_base.asset import Asset
from stellar_base.keypair import Keypair
from stellar_base.utils import XdrLengthError

import kin


def test_sdk_not_configured(setup):
    sdk = kin.SDK(horizon_endpoint_uri=setup.horizon_endpoint_uri, network=setup.network)
    with pytest.raises(kin.SdkError, message='address not configured'):
        sdk.get_address()
    with pytest.raises(kin.SdkError, message='address not configured'):
        sdk.get_native_balance()
    with pytest.raises(kin.SdkError, message='address not configured'):
        sdk.get_kin_balance()
    with pytest.raises(kin.SdkError, message='address not configured'):
        sdk.create_account('address')
    with pytest.raises(kin.SdkError, message='address not configured'):
        sdk.monitor_kin_payments(None)
    with pytest.raises(kin.SdkError, message='address not configured'):
        sdk._trust_asset(Asset('TMP', 'tmp'))
    with pytest.raises(kin.SdkError, message='address not configured'):
        sdk._send_asset(Asset('TMP', 'tmp'), 'address', 1)


def test_sdk_create_success(setup, test_sdk):
    assert test_sdk.horizon
    assert test_sdk.horizon.horizon_uri == setup.horizon_endpoint_uri
    assert test_sdk.network == setup.network
    assert test_sdk.base_keypair.verifying_key == setup.sdk_keypair.verifying_key
    assert test_sdk.base_keypair.signing_key == setup.sdk_keypair.signing_key
    assert test_sdk.channel_manager


def test_sdk_create_fail(setup, helpers, test_sdk):
    with pytest.raises(ValueError, message='invalid secret key: bad'):
        kin.SDK(secret_key='bad',
                horizon_endpoint_uri=setup.horizon_endpoint_uri, network=setup.network, kin_asset=setup.test_asset)

    keypair = Keypair.random()
    secret_key = keypair.seed()
    address = keypair.address().decode()

    with pytest.raises(ValueError, message='invalid channel key: bad'):
        kin.SDK(secret_key=secret_key, channel_secret_keys=['bad'],
                horizon_endpoint_uri=setup.horizon_endpoint_uri, network=setup.network, kin_asset=setup.test_asset)

    # wallet account does not exist
    with pytest.raises(kin.AccountNotFoundError):
        kin.SDK(secret_key=secret_key,
                horizon_endpoint_uri=setup.horizon_endpoint_uri, network=setup.network, kin_asset=setup.test_asset)

    helpers.fund_account(setup, address)

    # wallet account exists but not yet activated
    with pytest.raises(kin.AccountNotActivatedError):
        kin.SDK(secret_key=secret_key,
                horizon_endpoint_uri=setup.horizon_endpoint_uri, network=setup.network, kin_asset=setup.test_asset)

    helpers.trust_asset(setup, secret_key)

    channel_keypair = Keypair.random()
    channel_secret_key = channel_keypair.seed()

    # channel account does not exist
    with pytest.raises(kin.AccountNotFoundError):
        kin.SDK(secret_key=secret_key, channel_secret_keys=[channel_secret_key],
                horizon_endpoint_uri=setup.horizon_endpoint_uri, network=setup.network, kin_asset=setup.test_asset)

    # bad Horizon endpoint
    with pytest.raises(kin.NetworkError):
        kin.SDK(secret_key=secret_key,
                horizon_endpoint_uri='bad', network=setup.network, kin_asset=setup.test_asset)

    # no Horizon on endpoint
    with pytest.raises(kin.NetworkError):
        kin.SDK(secret_key=secret_key,
                horizon_endpoint_uri='http://localhost:666', network=setup.network, kin_asset=setup.test_asset)


def test_get_status(setup, test_sdk):
    # bad Horizon endpoint
    sdk = kin.SDK(horizon_endpoint_uri='bad')
    status = sdk.get_status()
    assert status['horizon']
    assert status['horizon']['online'] is False
    assert status['horizon']['error'].startswith("Invalid URL 'bad': No schema supplied")

    # no Horizon on endpoint
    sdk = kin.SDK(horizon_endpoint_uri='http://localhost:666')
    status = sdk.get_status()
    assert status['horizon']
    assert status['horizon']['online'] is False
    assert status['horizon']['error'].find('Connection refused') > 0

    # success
    status = test_sdk.get_status()
    assert status['network'] == setup.network
    assert status['address'] == setup.sdk_keypair.address().decode()
    assert status['kin_asset']
    assert status['kin_asset']['code'] == setup.test_asset.code
    assert status['kin_asset']['issuer'] == setup.test_asset.issuer
    assert status['horizon']
    assert status['horizon']['uri'] == setup.horizon_endpoint_uri
    assert status['horizon']['online']
    assert status['horizon']['error'] is None
    assert status['channels']
    assert status['channels']['all'] == 1
    assert status['channels']['free'] == 1


def test_get_address(setup, test_sdk):
    assert test_sdk.get_address() == setup.sdk_keypair.address().decode()


def test_get_native_balance(test_sdk):
    assert test_sdk.get_native_balance() > 9999


def test_check_account_exists(setup, test_sdk):
    with pytest.raises(ValueError, message='invalid address: bad'):
        test_sdk.check_account_exists('bad')

    keypair = Keypair.random()
    address = keypair.address().decode()

    assert not test_sdk.check_account_exists(address)

    address = setup.issuer_keypair.address().decode()
    assert test_sdk.check_account_exists(address)


def test_create_account(test_sdk):
    keypair = Keypair.random()
    address = keypair.address().decode()

    with pytest.raises(ValueError, message='invalid address: bad'):
        test_sdk.create_account('bad')

    # underfunded
    with pytest.raises(kin.LowBalanceError) as exc_info:
        test_sdk.create_account(address, starting_balance=1000000)
    assert exc_info.value.error_code == kin.CreateAccountResultCode.UNDERFUNDED

    # successful
    starting_balance = 100
    tx_hash = test_sdk.create_account(address, starting_balance=starting_balance, memo_text='foobar')
    assert tx_hash
    assert test_sdk.check_account_exists(address)
    assert test_sdk.get_account_native_balance(address) == starting_balance

    # test get_transaction_data for this transaction
    sleep(1)
    tx_data = test_sdk.get_transaction_data(tx_hash)
    assert tx_data
    assert tx_data.hash == tx_hash
    assert tx_data.source_account == test_sdk.get_address()
    assert tx_data.created_at
    assert tx_data.source_account_sequence
    assert tx_data.fee_paid == 100
    assert tx_data.memo_type == 'text'
    assert tx_data.memo == 'foobar'
    assert len(tx_data.signatures) == 1
    assert len(tx_data.operations) == 1

    op = tx_data.operations[0]
    assert op.id
    assert op.type == 'create_account'
    assert op.asset_code is None
    assert op.asset_type is None
    assert op.asset_issuer is None
    assert op.trustor is None
    assert op.trustee is None
    assert op.limit is None
    assert op.from_address is None
    assert op.to_address is None
    assert op.amount is None

    with pytest.raises(kin.AccountExistsError) as exc_info:
        test_sdk.create_account(address)
    assert exc_info.value.error_code == kin.CreateAccountResultCode.ACCOUNT_EXISTS


def test_get_account_asset_balance_fail(test_sdk, setup):
    with pytest.raises(ValueError, message='invalid address: bad'):
        test_sdk._get_account_asset_balance('bad', setup.test_asset)

    keypair = Keypair.random()
    address = keypair.address().decode()

    with pytest.raises(ValueError, message='invalid asset issuer: bad'):
        test_sdk._get_account_asset_balance(address, Asset('TMP', 'bad'))

    # account not created yet
    with pytest.raises(kin.AccountNotFoundError) as exc_info:
        test_sdk._get_account_asset_balance(address, setup.test_asset)

    assert test_sdk.create_account(address, starting_balance=10)

    with pytest.raises(kin.AccountNotActivatedError) as exc_info:
        test_sdk._get_account_asset_balance(address, setup.test_asset)


def test_send_native(test_sdk):
    with pytest.raises(ValueError, message='invalid address: bad'):
        test_sdk.send_native('bad', 100)

    keypair = Keypair.random()
    address = keypair.address().decode()

    with pytest.raises(ValueError, message='amount must be positive'):
        test_sdk.send_native(address, 0)

    # account does not exist yet
    with pytest.raises(kin.AccountNotFoundError) as exc_info:
        test_sdk.send_native(address, 100)
    assert exc_info.value.error_code == kin.PaymentResultCode.NO_DESTINATION

    assert test_sdk.create_account(address, starting_balance=100)

    # check underfunded
    with pytest.raises(kin.LowBalanceError) as exc_info:
        test_sdk.send_native(address, 1000000)
    assert exc_info.value.error_code == kin.PaymentResultCode.UNDERFUNDED

    # send and check the resulting balance
    tx_hash = test_sdk.send_native(address, 10.123, memo_text='foobar')
    assert tx_hash

    assert test_sdk.get_account_native_balance(address) == Decimal('110.123')

    # test get_transaction_data for this transaction
    sleep(1)
    tx_data = test_sdk.get_transaction_data(tx_hash)
    assert tx_data
    assert tx_data.hash == tx_hash
    assert tx_data.source_account == test_sdk.get_address()
    assert tx_data.created_at
    assert tx_data.source_account_sequence
    assert tx_data.fee_paid == 100
    assert tx_data.memo_type == 'text'
    assert tx_data.memo == 'foobar'
    assert len(tx_data.signatures) == 1
    assert len(tx_data.operations) == 1

    op = tx_data.operations[0]
    assert op.id
    assert op.type == 'payment'
    assert op.asset_code is None
    assert op.asset_type == 'native'
    assert op.asset_issuer is None
    assert op.trustor is None
    assert op.trustee is None
    assert op.limit is None
    assert op.from_address == test_sdk.get_address()
    assert op.to_address == address
    assert op.amount == Decimal('10.123')

    # check several payments in a row
    tx_hash1 = test_sdk.send_native(address, 1)
    assert tx_hash1
    tx_hash2 = test_sdk.send_native(address, 1)
    assert tx_hash2
    tx_hash3 = test_sdk.send_native(address, 1)
    assert tx_hash3

    sleep(1)
    tx_data = test_sdk.get_transaction_data(tx_hash1)
    assert tx_data.hash == tx_hash1
    tx_data = test_sdk.get_transaction_data(tx_hash2)
    assert tx_data.hash == tx_hash2
    tx_data = test_sdk.get_transaction_data(tx_hash3)
    assert tx_data.hash == tx_hash3


def test_trust_asset(setup, test_sdk, helpers):
    # failures
    with pytest.raises(Exception, message='Issuer cannot be null'):
        test_sdk._trust_asset(Asset(''))
    with pytest.raises(XdrLengthError, message='Asset code must be 12 characters at max.'):
        test_sdk._trust_asset(Asset('abcdefghijklmnopqr'))
    with pytest.raises(Exception, message='Issuer cannot be null'):
        test_sdk._trust_asset(Asset('TMP'))
    with pytest.raises(ValueError, message='asset issuer invalid'):
        test_sdk._trust_asset(Asset('TMP', 'tmp'))

    # success
    tx_hash = test_sdk._trust_asset(setup.test_asset, limit=1000, memo_text='foobar')
    assert tx_hash
    assert test_sdk._check_asset_trusted(test_sdk.get_address(), setup.test_asset)
    # TODO: check asset limit

    # test get_transaction_data for this transaction
    sleep(1)
    tx_data = test_sdk.get_transaction_data(tx_hash)
    assert tx_data
    assert tx_data.hash == tx_hash
    assert tx_data.source_account == test_sdk.get_address()
    assert tx_data.created_at
    assert tx_data.source_account_sequence
    assert tx_data.fee_paid == 100
    assert tx_data.memo_type == 'text'
    assert tx_data.memo == 'foobar'
    assert len(tx_data.signatures) == 1
    assert len(tx_data.operations) == 1

    op = tx_data.operations[0]
    assert op.id
    # assert op.created_at
    # assert op.transaction_hash == tx_hash
    assert op.type == 'change_trust'
    assert op.asset_code == setup.test_asset.code
    assert op.asset_type == 'credit_alphanum4'
    assert op.asset_issuer == setup.test_asset.issuer
    assert op.trustor == test_sdk.get_address()
    assert op.trustee == setup.test_asset.issuer
    assert op.limit == Decimal('1000')
    assert op.from_address is None
    assert op.to_address is None
    assert op.amount is None

    # finally, fund the sdk account with asset
    assert helpers.fund_asset(setup, test_sdk.get_address(), 1000)
    assert test_sdk._get_account_asset_balance(test_sdk.get_address(), setup.test_asset) == Decimal('1000')


def test_asset_trusted(setup, test_sdk):
    with pytest.raises(ValueError, message='invalid address: bad'):
        test_sdk._check_asset_trusted('bad', setup.test_asset)

    keypair = Keypair.random()
    address = keypair.address().decode()

    with pytest.raises(ValueError, message='invalid asset issuer: bad'):
        test_sdk._check_asset_trusted(address, Asset('TMP', 'bad'))

    with pytest.raises(kin.AccountNotFoundError):
        test_sdk._check_asset_trusted(address, setup.test_asset)

    assert test_sdk.create_account(address, starting_balance=100)

    assert not test_sdk._check_asset_trusted(address, setup.test_asset)


def test_send_asset(setup, test_sdk, helpers):
    with pytest.raises(ValueError, message='invalid address: bad'):
        test_sdk._send_asset(setup.test_asset, 'bad', 10)

    keypair = Keypair.random()
    address = keypair.address().decode()

    with pytest.raises(ValueError, message='amount must be positive'):
        test_sdk._send_asset(setup.test_asset, address, 0)

    with pytest.raises(ValueError, message='invalid asset issuer: bad'):
        test_sdk._send_asset(Asset('TMP', 'bad'), address, 10)

    # account does not exist yet
    with pytest.raises(kin.AccountNotFoundError) as exc_info:
        test_sdk._send_asset(setup.test_asset, address, 10)
    assert exc_info.value.error_code == kin.PaymentResultCode.NO_DESTINATION

    assert test_sdk.create_account(address, starting_balance=100)

    # no trustline yet
    with pytest.raises(kin.AccountNotActivatedError) as exc_info:
        test_sdk._send_asset(setup.test_asset, address, 10)
    assert exc_info.value.error_code == kin.PaymentResultCode.NO_TRUST

    # add trustline from the newly created account to the kin issuer
    assert helpers.trust_asset(setup, keypair.seed())

    # send and check the resulting balance
    tx_hash = test_sdk._send_asset(setup.test_asset, address, 10.123, memo_text='foobar')
    assert tx_hash
    assert test_sdk._get_account_asset_balance(address, setup.test_asset) == Decimal('10.123')

    # test get_transaction_data for this transaction
    sleep(1)
    tx_data = test_sdk.get_transaction_data(tx_hash)
    assert tx_data
    assert tx_data.hash == tx_hash
    assert tx_data.source_account == test_sdk.get_address()
    assert tx_data.created_at
    assert tx_data.source_account_sequence
    assert tx_data.fee_paid == 100
    assert tx_data.memo_type == 'text'
    assert tx_data.memo == 'foobar'
    assert len(tx_data.signatures) == 1
    assert len(tx_data.operations) == 1

    op = tx_data.operations[0]
    assert op.id
    assert op.type == 'payment'
    assert op.asset_code == setup.test_asset.code
    assert op.asset_type == 'credit_alphanum4'
    assert op.asset_issuer == setup.test_asset.issuer
    assert op.trustor is None
    assert op.trustee is None
    assert op.limit is None
    assert op.from_address == test_sdk.get_address()
    assert op.to_address == address
    assert op.amount == Decimal('10.123')


def test_get_account_data(setup, test_sdk):
    with pytest.raises(ValueError, message='invalid address: bad'):
        test_sdk.get_account_data('bad')

    address = Keypair.random().address().decode()
    with pytest.raises(kin.AccountNotFoundError):
        test_sdk.get_account_data(address)

    acc_data = test_sdk.get_account_data(test_sdk.get_address())
    assert acc_data
    assert acc_data.id == test_sdk.get_address()
    assert acc_data.sequence
    assert acc_data.data == {}

    assert acc_data.thresholds
    assert acc_data.thresholds.low_threshold == 0
    assert acc_data.thresholds.medium_threshold == 0
    assert acc_data.thresholds.high_threshold == 0

    assert acc_data.flags
    assert not acc_data.flags.auth_revocable
    assert not acc_data.flags.auth_required

    assert len(acc_data.balances) == 2
    asset_balance = acc_data.balances[0]
    native_balance = acc_data.balances[1]
    assert asset_balance.balance > 900
    assert asset_balance.limit == Decimal('1000')
    assert asset_balance.asset_type == 'credit_alphanum4'
    assert asset_balance.asset_code == setup.test_asset.code
    assert asset_balance.asset_issuer == setup.test_asset.issuer
    assert native_balance.balance > 9000
    assert native_balance.asset_type == 'native'

    # just to increase test coverage
    assert str(acc_data)


def test_get_transaction_data_fail(test_sdk):
    with pytest.raises(ValueError, message='invalid transaction hash: bad'):
        test_sdk.get_transaction_data('bad')

    with pytest.raises(kin.ResourceNotFoundError):
        test_sdk.get_transaction_data('c2a9d905a728ae918bf50058548f2421463ae09e1302be8e5b4b882c81c2edb8')


def test_monitor_accounts_transactions_fail(setup, test_sdk):
    with pytest.raises(ValueError, message='invalid asset issuer: bad'):
        test_sdk._monitor_accounts_transactions(Asset('TMP', 'bad'), None, None)

    with pytest.raises(ValueError, message='no addresses to monitor'):
        test_sdk._monitor_accounts_transactions(setup.test_asset, [], None)

    with pytest.raises(ValueError, message='invalid address: bad'):
        test_sdk._monitor_accounts_transactions(setup.test_asset, ['bad'], None)

    keypair = Keypair.random()
    address = keypair.address().decode()

    with pytest.raises(kin.AccountNotFoundError):
        test_sdk.monitor_accounts_transactions([address], None)

    with pytest.raises(kin.AccountNotFoundError):
        test_sdk._monitor_accounts_transactions(setup.test_asset, [address], None)


def test_monitor_accounts_transactions(setup, test_sdk, helpers):
    keypair = Keypair.random()
    address = keypair.address().decode()

    tx_hash1 = test_sdk.create_account(address, starting_balance=100, memo_text='create')
    assert tx_hash1

    ev = threading.Event()
    tx_datas = []

    def account_tx_callback(addr, tx_data):
        assert addr == address
        tx_datas.append(tx_data)
        if len(tx_datas) == 4:  # create/trust/send_asset/send_native
            ev.set()

    # start monitoring
    sleep(1)
    test_sdk.monitor_accounts_transactions([address], account_tx_callback)

    tx_hash2 = helpers.trust_asset(setup, keypair.seed(), memo_text='trust')
    assert tx_hash2

    tx_hash3 = test_sdk._send_asset(setup.test_asset, address, 10, memo_text='send asset')
    assert tx_hash3

    tx_hash4 = test_sdk.send_native(address, 1, memo_text='send native')
    assert tx_hash4

    # wait until callback gets them all
    assert ev.wait(3)

    # check collected transactions
    assert tx_datas[0].hash == tx_hash1
    assert tx_datas[0].source_account == test_sdk.get_address()
    assert tx_datas[0].memo == 'create'
    assert tx_datas[0].operations[0].type == 'create_account'

    assert tx_datas[1].hash == tx_hash2
    assert tx_datas[1].source_account == address
    assert tx_datas[1].memo == 'trust'
    assert tx_datas[1].operations[0].type == 'change_trust'

    assert tx_datas[2].hash == tx_hash3
    assert tx_datas[2].source_account == test_sdk.get_address()
    assert tx_datas[2].memo == 'send asset'
    assert tx_datas[2].operations[0].type == 'payment'
    assert tx_datas[2].operations[0].asset_code == setup.test_asset.code

    assert tx_datas[3].hash == tx_hash4
    assert tx_datas[3].source_account == test_sdk.get_address()
    assert tx_datas[3].memo == 'send native'
    assert tx_datas[3].operations[0].type == 'payment'
    assert tx_datas[3].operations[0].asset_type == 'native'


def test_monitor_asset_transactions_single(setup, test_sdk, helpers):
    keypair = Keypair.random()
    address = keypair.address().decode()

    assert test_sdk.create_account(address, starting_balance=100, memo_text='create')
    assert helpers.trust_asset(setup, keypair.seed(), memo_text='trust')
    
    ev = threading.Event()
    tx_datas = []

    def account_tx_callback(addr, tx_data):
        assert addr == address
        tx_datas.append(tx_data)
        if len(tx_datas) == 2:
            ev.set()

    # start monitoring
    sleep(1)
    test_sdk._monitor_accounts_transactions(setup.test_asset, [address],
                                            account_tx_callback, only_payments=True)

    # pay from sdk to the account
    tx_hash1 = test_sdk._send_asset(setup.test_asset, address, 10)
    assert tx_hash1
    
    # pay from the account back to the sdk
    tx_hash2 = helpers.send_asset(setup, keypair.seed(), test_sdk.get_address(), 10)
    assert tx_hash2
    
    # wait until the callback gets them all
    assert ev.wait(3)

    # check collected transactions
    assert tx_datas[0].hash == tx_hash1
    op_data = tx_datas[0].operations[0]
    assert op_data.type == 'payment'
    assert op_data.asset_code == setup.test_asset.code
    assert op_data.asset_issuer == setup.test_asset.issuer
    assert op_data.from_address == test_sdk.get_address()
    assert op_data.to_address == address
    assert op_data.amount == Decimal('10')

    assert tx_datas[1].hash == tx_hash2
    op_data = tx_datas[1].operations[0]
    assert op_data.type == 'payment'
    assert op_data.asset_code == setup.test_asset.code
    assert op_data.asset_issuer == setup.test_asset.issuer
    assert op_data.from_address == address
    assert op_data.to_address == test_sdk.get_address()
    assert op_data.amount == Decimal('10')


def test_monitor_asset_transactions_multiple(setup, test_sdk, helpers):
    keypair1 = Keypair.random()
    address1 = keypair1.address().decode()
    keypair2 = Keypair.random()
    address2 = keypair2.address().decode()

    assert test_sdk.create_account(address1, starting_balance=100)
    assert test_sdk.create_account(address2, starting_balance=100)
    assert helpers.trust_asset(setup, keypair1.seed())
    assert helpers.trust_asset(setup, keypair2.seed())

    ev1 = threading.Event()
    ev2 = threading.Event()
    tx_datas1 = []
    tx_datas2 = []

    def account_tx_callback(addr, tx_data):
        assert addr == address1 or addr == address2
        op_data = tx_data.operations[0]
        if op_data.to_address == address1:
            tx_datas1.append(tx_data)
            ev1.set()
        elif op_data.to_address == address2:
            tx_datas2.append(tx_data)
            ev2.set()

    # start monitoring
    sleep(1)
    test_sdk._monitor_accounts_transactions(setup.test_asset, [address1, address2],
                                            account_tx_callback, only_payments=True)

    # send payments
    tx_hash12 = test_sdk._send_asset(setup.test_asset, address1, 10)
    assert tx_hash12
    tx_hash22 = test_sdk._send_asset(setup.test_asset, address2, 10)
    assert tx_hash22

    # wait until callback gets them all
    assert ev1.wait(3)
    assert ev2.wait(3)

    # check collected operations
    assert tx_datas1[0].hash == tx_hash12
    op_data = tx_datas1[0].operations[0]
    assert op_data.type == 'payment'
    assert op_data.asset_code == setup.test_asset.code
    assert op_data.asset_issuer == setup.test_asset.issuer
    assert op_data.from_address == test_sdk.get_address()
    assert op_data.to_address == address1
    assert op_data.amount == Decimal('10')

    assert tx_datas2[0].hash == tx_hash22
    op_data = tx_datas2[0].operations[0]
    assert op_data.type == 'payment'
    assert op_data.asset_code == setup.test_asset.code
    assert op_data.asset_issuer == setup.test_asset.issuer
    assert op_data.from_address == test_sdk.get_address()
    assert op_data.to_address == address2
    assert op_data.amount == Decimal('10')


def test_channels(setup, helpers):
    # prepare channel accounts
    channel_keypairs = [Keypair.random(), Keypair.random(), Keypair.random(), Keypair.random()]
    channel_keys = [channel_keypair.seed() for channel_keypair in channel_keypairs]
    channel_addresses = [channel_keypair.address().decode() for channel_keypair in channel_keypairs]
    for channel_address in channel_addresses:
        helpers.fund_account(setup, channel_address)

    # init sdk with these channels
    sdk = kin.SDK(secret_key=setup.sdk_keypair.seed(),channel_secret_keys=channel_keys,
                  horizon_endpoint_uri=setup.horizon_endpoint_uri, network=setup.network, kin_asset=setup.test_asset)

    assert sdk
    assert sdk.channel_manager
    assert sdk.channel_manager.channel_builders.qsize() == len(channel_keypairs)

    thread_ex = []

    def channel_worker(thread_ex_holder):
        try:
            # create an account using a channel
            address = Keypair.random().address().decode()
            tx_hash1 = sdk.create_account(address, starting_balance=100)
            assert tx_hash1
            # send lumens
            tx_hash2 = sdk.send_native(address, 1)
            assert tx_hash2
            # send more lumens
            tx_hash3 = sdk.send_native(address, 1)
            assert tx_hash3

            sleep(1)

            # check transactions
            tx_data = sdk.get_transaction_data(tx_hash1)
            assert tx_data
            # transaction envelope source is some channel account
            assert tx_data.source_account in channel_addresses
            # operation source is the base account
            assert tx_data.operations[0].source_account == sdk.get_address()

            tx_data = sdk.get_transaction_data(tx_hash2)
            assert tx_data
            assert tx_data.source_account in channel_addresses
            assert tx_data.operations[0].source_account == sdk.get_address()

            tx_data = sdk.get_transaction_data(tx_hash3)
            assert tx_data
            assert tx_data.source_account in channel_addresses
            assert tx_data.operations[0].source_account == sdk.get_address()
        except Exception as e:
            thread_ex_holder.append(e)

    # now issue parallel transactions
    threads = []
    for channel_keypair in channel_keypairs:
        t = threading.Thread(target=channel_worker, args=(thread_ex,))
        threads.append(t)
    for t in threads:
        t.start()

    # wait for all to finish
    for t in threads:
        t.join()

    # check thread errors
    assert not thread_ex

