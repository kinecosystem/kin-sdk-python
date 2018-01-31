from decimal import Decimal
import json
import requests
import pytest
import threading
from time import sleep

from stellar_base.asset import Asset
from stellar_base.keypair import Keypair
from stellar_base.utils import XdrLengthError

import kin
from kin.builder import Builder


def test_sdk_create_fail():
    # bad endpoint
    with pytest.raises(kin.SdkConfigurationError, match='cannot connect to horizon'):
        kin.SDK(horizon_endpoint_uri='bad')
    with pytest.raises(kin.SdkConfigurationError, match='cannot connect to horizon'):
        kin.SDK(horizon_endpoint_uri='http://localhost:666')

    # bad seeds (without Nick Cave)
    with pytest.raises(kin.SdkConfigurationError, match='invalid base seed'):
        kin.SDK(base_seed='bad')

    keypair = Keypair.random()
    with pytest.raises(kin.SdkConfigurationError, match='invalid channel seed'):
        kin.SDK(base_seed=keypair.seed(), channel_seeds=['bad'])


def test_sdk_not_configured():
    sdk = kin.SDK()
    with pytest.raises(kin.SdkNotConfiguredError, match='address not configured'):
        sdk.get_address()
    with pytest.raises(kin.SdkNotConfiguredError, match='address not configured'):
        sdk.get_lumen_balance()
    with pytest.raises(kin.SdkNotConfiguredError, match='address not configured'):
        sdk.get_kin_balance()
    with pytest.raises(kin.SdkNotConfiguredError, match='address not configured'):
        sdk.create_account('address')
    with pytest.raises(kin.SdkNotConfiguredError, match='address not configured'):
        sdk.trust_asset(Asset('TMP', 'tmp'))
    with pytest.raises(kin.SdkNotConfiguredError, match='address not configured'):
        sdk.send_asset('address', Asset('TMP', 'tmp'), 1)
    with pytest.raises(kin.SdkNotConfiguredError, match='address not configured'):
        sdk.monitor_transactions(None)


def test_sdk_create_success():
    keypair = Keypair.random()
    sdk = kin.SDK(base_seed=keypair.seed())
    assert sdk
    assert sdk.horizon
    assert sdk.network == 'PUBLIC'
    assert sdk.base_keypair.verifying_key == keypair.verifying_key
    assert sdk.base_keypair.signing_key == keypair.signing_key
    assert sdk.channel_manager


@pytest.fixture(scope='session')
def setup(testnet):
    class Struct:
        """Handy variable holder"""
        def __init__(self, **entries): self.__dict__.update(entries)

    sdk_keypair = Keypair.random()
    issuer_keypair = Keypair.random()
    test_asset = Asset('KIN', issuer_keypair.address().decode())

    # global testnet
    if testnet:
        from stellar_base.horizon import HORIZON_TEST
        return Struct(type='testnet',
                      network='TESTNET',
                      sdk_keypair=sdk_keypair,
                      issuer_keypair=issuer_keypair,
                      test_asset=test_asset,
                      horizon_endpoint_uri=HORIZON_TEST)

    # local testnet (zulucrypto docker)
    # https://github.com/zulucrypto/docker-stellar-integration-test-network
    from stellar_base.network import NETWORKS
    NETWORKS['CUSTOM'] = 'Integration Test Network ; zulucrypto'
    return Struct(type='local',
                  network='CUSTOM',
                  sdk_keypair=sdk_keypair,
                  issuer_keypair=issuer_keypair,
                  test_asset=test_asset,
                  horizon_endpoint_uri='http://localhost:8000')


@pytest.fixture(scope='session')
def test_sdk(setup):
    # create and fund sdk account
    fund(setup, setup.sdk_keypair.address().decode())

    # create and fund issuer account
    fund(setup, setup.issuer_keypair.address().decode())

    # override KIN with our test asset
    # TODO: does not work?
    kin.KIN_ASSET = setup.test_asset

    # init sdk
    sdk = kin.SDK(base_seed=setup.sdk_keypair.seed(), horizon_endpoint_uri=setup.horizon_endpoint_uri, network=setup.network)
    assert sdk
    return sdk


def test_get_address(setup, test_sdk):
    assert test_sdk.get_address() == setup.sdk_keypair.address().decode()


def test_get_lumen_balance(test_sdk):
    assert test_sdk.get_lumen_balance() == 10000


def test_get_address_asset_balance(test_sdk, setup):
    with pytest.raises(ValueError, match='invalid address'):
        test_sdk.get_address_asset_balance('bad', setup.test_asset)

    keypair = Keypair.random()
    address = keypair.address().decode()

    with pytest.raises(ValueError, match='asset issuer invalid'):
        test_sdk.get_address_asset_balance(address, Asset('TMP', 'bad'))

    with pytest.raises(kin.SdkHorizonError, match='Resource Missing'):
        test_sdk.get_address_asset_balance(address, setup.test_asset)

    # success is tested below

def test_check_account_exists(setup, test_sdk):
    with pytest.raises(ValueError, match='invalid address'):
        test_sdk.check_account_exists('bad')

    keypair = Keypair.random()
    address = keypair.address().decode()

    assert not test_sdk.check_account_exists(address)

    address = setup.issuer_keypair.address().decode()
    assert test_sdk.check_account_exists(address)


def test_create_account(test_sdk):
    keypair = Keypair.random()
    address = keypair.address().decode()

    with pytest.raises(ValueError, match='invalid address'):
        test_sdk.create_account('bad')

    # underfunded
    with pytest.raises(kin.SdkHorizonError, match=kin.CreateAccountResultCode.UNDERFUNDED):
        test_sdk.create_account(address, starting_balance=1000000)

    # successful
    starting_balance = 100
    tx_hash = test_sdk.create_account(address, starting_balance=starting_balance, memo_text='foobar')
    assert tx_hash
    assert test_sdk.check_account_exists(address)
    assert test_sdk.get_address_lumen_balance(address) == starting_balance

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


def test_send_lumens(test_sdk):
    with pytest.raises(ValueError, match='invalid address'):
        test_sdk.send_lumens('bad', 100)

    keypair = Keypair.random()
    address = keypair.address().decode()

    with pytest.raises(ValueError, match='amount must be positive'):
        test_sdk.send_lumens(address, 0)

    # account does not exist yet
    with pytest.raises(kin.SdkHorizonError, match=kin.PaymentResultCode.NO_DESTINATION):
        test_sdk.send_lumens(address, 100)

    tx_hash = test_sdk.create_account(address, starting_balance=100)
    assert tx_hash

    # check underfunded
    with pytest.raises(kin.SdkHorizonError, match=kin.PaymentResultCode.UNDERFUNDED):
        test_sdk.send_lumens(address, 1000000)

    tx_hash = test_sdk.send_lumens(address, 10.123, memo_text='foobar')
    assert tx_hash

    assert test_sdk.get_address_lumen_balance(address) == Decimal('110.123')

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
    assert op.from_address is None
    assert op.to_address is None
    assert op.amount == Decimal('10.123')


def test_trust_asset(setup, test_sdk):
    # failures
    with pytest.raises(Exception, match='Issuer cannot be null'):
        test_sdk.trust_asset(Asset(''))
    with pytest.raises(XdrLengthError, match='Asset code must be 12 characters at max.'):
        test_sdk.trust_asset(Asset('abcdefghijklmnopqr'))
    with pytest.raises(Exception, match='Issuer cannot be null'):
        test_sdk.trust_asset(Asset('TMP'))
    with pytest.raises(ValueError, match='asset issuer invalid'):
        test_sdk.trust_asset(Asset('TMP', 'tmp'))

    # success
    tx_hash = test_sdk.trust_asset(setup.test_asset, limit=1000, memo_text='foobar')
    assert tx_hash
    assert test_sdk.check_asset_trusted(test_sdk.get_address(), setup.test_asset)
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
    assert fund_asset(setup, test_sdk.get_address(), 1000)
    assert test_sdk.get_address_asset_balance(test_sdk.get_address(), setup.test_asset) == Decimal('1000')


def test_asset_trusted(setup, test_sdk):
    with pytest.raises(ValueError, match='invalid address'):
        test_sdk.check_asset_trusted('bad', setup.test_asset)

    keypair = Keypair.random()
    address = keypair.address().decode()

    with pytest.raises(ValueError, match='asset issuer invalid'):
        test_sdk.check_asset_trusted(address, Asset('TMP', 'bad'))

    with pytest.raises(kin.SdkHorizonError, match='Resource Missing'):
        test_sdk.check_asset_trusted(address, setup.test_asset)

    tx_hash = test_sdk.create_account(address, starting_balance=100)
    assert tx_hash

    assert not test_sdk.check_asset_trusted(address, setup.test_asset)


def test_send_asset(setup, test_sdk):
    with pytest.raises(ValueError, match='invalid address'):
        test_sdk.send_asset('bad', setup.test_asset, 10)

    keypair = Keypair.random()
    address = keypair.address().decode()

    with pytest.raises(ValueError, match='amount must be positive'):
        test_sdk.send_asset(address, setup.test_asset, 0)

    with pytest.raises(ValueError, match='asset issuer invalid'):
        test_sdk.send_asset(address, Asset('TMP', 'bad'), 10)

    # account does not exist yet
    with pytest.raises(kin.SdkHorizonError, match=kin.PaymentResultCode.NO_DESTINATION):
        test_sdk.send_asset(address, setup.test_asset, 10)

    tx_hash = test_sdk.create_account(address, starting_balance=100)
    assert tx_hash

    # no trustline yet
    with pytest.raises(kin.SdkHorizonError, match=kin.PaymentResultCode.NO_TRUST):
        test_sdk.send_asset(address, setup.test_asset, 10)

    # add trustline from the newly created account to the kin issuer
    assert trust_asset(setup, test_sdk, keypair.seed())

    # send asset
    tx_hash = test_sdk.send_asset(address, setup.test_asset, 10.123, memo_text='foobar')
    assert tx_hash
    assert test_sdk.get_address_asset_balance(address, setup.test_asset) == Decimal('10.123')

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
    assert op.from_address is None
    assert op.to_address is None
    assert op.amount == Decimal('10.123')


def test_get_account_data(setup, test_sdk):
    with pytest.raises(ValueError, match='invalid address'):
        test_sdk.get_account_data('bad')

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


def test_get_transaction_data(test_sdk):
    with pytest.raises(kin.SdkHorizonError, match='Resource Missing'):
        test_sdk.get_transaction_data('bad')


def test_monitor_address_transactions(setup, test_sdk):
    keypair = Keypair.random()
    address = keypair.address().decode()

    with pytest.raises(Exception, match='404 Client Error: Not Found'):  # TODO: why not consistent?
        test_sdk.monitor_address_transactions(address, None)

    tx_hash1 = test_sdk.create_account(address, starting_balance=100, memo_text='create')
    assert tx_hash1

    import threading
    ev = threading.Event()

    tx_datas = []

    def account_tx_callback(tx_data):
        tx_datas.append(tx_data)
        if len(tx_datas) == 3:  # create/trust/send_asset
            ev.set()

    # start monitoring
    sleep(1)
    test_sdk.monitor_address_transactions(address, account_tx_callback)

    # issue the second and third transactions (the first is account creation)
    tx_hash2 = trust_asset(setup, test_sdk, keypair.seed(), memo_text='trust')
    assert tx_hash2
    tx_hash3 = test_sdk.send_asset(address, setup.test_asset, 10.123, memo_text='send')
    assert tx_hash3

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
    assert tx_datas[2].memo == 'send'
    assert tx_datas[2].operations[0].type == 'payment'


def test_channels(setup):
    # prepare channel accounts
    channel_keypairs = [Keypair.random(), Keypair.random(), Keypair.random(), Keypair.random()]
    channel_seeds = [channel_keypair.seed() for channel_keypair in channel_keypairs]
    channel_addresses = [channel_keypair.address().decode() for channel_keypair in channel_keypairs]
    for channel_address in channel_addresses:
        fund(setup, channel_address)

    # init sdk with these channels
    sdk = kin.SDK(base_seed=setup.sdk_keypair.seed(), horizon_endpoint_uri=setup.horizon_endpoint_uri,
                  network=setup.network, channel_seeds=channel_seeds)
    assert sdk
    assert sdk.channel_manager
    assert sdk.channel_manager.channel_builders.qsize() == len(channel_keypairs)

    def channel_worker():
        # create an account using a channel
        address = Keypair.random().address().decode()
        tx_hash = sdk.create_account(address, starting_balance=100)
        assert tx_hash
        sleep(1)
        tx_data = sdk.get_transaction_data(tx_hash)
        assert tx_data
        # transaction envelope source is some channel account
        assert tx_data.source_account in channel_addresses
        # operation source is the base account
        assert tx_data.operations[0].source_account == sdk.get_address()

    # now issue parallel transactions
    threads = []
    for channel_keypair in channel_keypairs:
        t = threading.Thread(target=channel_worker)
        threads.append(t)
    for t in threads:
        t.start()

    # wait for all to finish
    for t in threads:
        t.join()


# helpers


def fund(setup, address):
    for attempt in range(3):
        r = requests.get(setup.horizon_endpoint_uri + '/friendbot?addr=' + address)  # Get 10000 lumens
        j = json.loads(r.text)
        if 'hash' in j or 'op_already_exists' in j:
            return
    raise Exception('account funding failed')


def fund_asset(setup, address, amount, memo_text=None):
    builder = Builder(secret=setup.issuer_keypair.seed(), horizon=setup.horizon_endpoint_uri, network=setup.network)
    builder.append_payment_op(address, amount, asset_type=setup.test_asset.code, asset_issuer=setup.test_asset.issuer)
    if memo_text:
        builder.add_text_memo(memo_text[:28])  # max memo length is 28
    builder.sign()
    reply = builder.submit()
    kin.check_horizon_reply(reply)
    return reply.get('hash')


def trust_asset(setup, test_sdk, seed, memo_text=None):
    builder = Builder(secret=seed, horizon=test_sdk.horizon.horizon, network=test_sdk.network)
    builder.append_trust_op(setup.test_asset.issuer, setup.test_asset.code)
    if memo_text:
        builder.add_text_memo(memo_text[:28])  # max memo length is 28
    builder.sign()
    reply = builder.submit()
    kin.check_horizon_reply(reply)
    return reply.get('hash')

