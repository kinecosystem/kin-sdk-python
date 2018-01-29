from decimal import Decimal
import json
import requests
import pytest
from time import sleep

from stellar_base.asset import Asset
from stellar_base.keypair import Keypair
from stellar_base.utils import XdrLengthError, DecodeError

import kin
from kin.builder import Builder


#TEST_SEED = 'SAWNYEI5LGSCFIOTMZVND5BDWM7REDOK2TWNBFAQXINLBKYYBUR6A2M7'  # GDQNZRZAU5D5MYSMQX7VNANEVXF6IEIYKAP3TK6WX5HYBV6FGATJ462F
#TEST_KEYPAIR = Keypair.from_seed(TEST_SEED)


def test_sdk_create_fail():
    # bad endpoint
    with pytest.raises(kin.SdkConfigurationError, match='cannot connect to horizon'):
        kin.SDK(horizon_endpoint_uri='bad')
    with pytest.raises(kin.SdkConfigurationError, match='cannot connect to horizon'):
        kin.SDK(horizon_endpoint_uri='http://localhost:666')

    # bad seed
    with pytest.raises(Exception, match='Incorrect padding'):  # TODO: change error
        kin.SDK(seed='bad')


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


def test_sdk_create_success():
    keypair = Keypair.random()
    sdk = kin.SDK(seed=keypair.seed())
    assert sdk
    assert sdk.horizon
    assert sdk.network == 'PUBLIC'
    assert sdk.keypair.verifying_key == keypair.verifying_key
    assert sdk.keypair.signing_key == keypair.signing_key
    assert sdk.builder


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
    kin.KIN_ASSET = setup.test_asset

    # init sdk
    sdk = kin.SDK(seed=setup.sdk_keypair.seed(), horizon_endpoint_uri=setup.horizon_endpoint_uri, network=setup.network)
    assert sdk
    return sdk


def test_get_address(test_sdk, setup):
    assert test_sdk.get_address() == setup.sdk_keypair.address().decode()


def test_get_lumen_balance(test_sdk):
    assert test_sdk.get_lumen_balance() == 10000


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

    # underfunded
    with pytest.raises(kin.SdkHorizonError, match=kin.CreateAccountResultCode.UNDERFUNDED):
        test_sdk.create_account(address, starting_balance=1000000)

    # successful
    starting_balance = 100
    tx_hash = test_sdk.create_account(address, starting_balance=starting_balance)
    assert tx_hash
    assert test_sdk.check_account_exists(address)
    assert test_sdk.get_address_lumen_balance(address) == starting_balance


def test_send_lumens(test_sdk):
    with pytest.raises(ValueError, match='invalid address'):
        test_sdk.send_lumens('bad', 100)

    keypair = Keypair.random()
    address = keypair.address().decode()

    with pytest.raises(ValueError, match='amount must be positive'):
        test_sdk.send_lumens(address, 0)

    with pytest.raises(kin.SdkHorizonError, match=kin.PaymentResultCode.NO_DESTINATION):
        test_sdk.send_lumens(address, 100)

    tx_hash = test_sdk.create_account(address, starting_balance=100)
    assert tx_hash

    with pytest.raises(kin.SdkHorizonError, match=kin.PaymentResultCode.UNDERFUNDED):
        test_sdk.send_lumens(address, 1000000)

    tx_hash = test_sdk.send_lumens(address, 10.123)
    assert tx_hash

    assert test_sdk.get_address_lumen_balance(address) == Decimal('110.123')


def test_trust_asset_failed(test_sdk):
    with pytest.raises(Exception, match='Issuer cannot be null'):
        test_sdk.trust_asset(Asset(''))
    with pytest.raises(XdrLengthError, match='Asset code must be 12 characters at max.'):
        test_sdk.trust_asset(Asset('abcdefghijklmnopqr'))
    with pytest.raises(Exception, match='Issuer cannot be null'):
        test_sdk.trust_asset(Asset('TMP'))
    with pytest.raises(ValueError, match='asset issuer invalid'):
        test_sdk.trust_asset(Asset('TMP', 'tmp'))


def test_trust_asset(setup, test_sdk):
    tx_hash = test_sdk.trust_asset(setup.test_asset, limit=1000)
    assert tx_hash
    assert test_sdk.check_asset_trusted(test_sdk.get_address(), setup.test_asset)
    # TODO: check limit

    # now fund the sdk account with asset
    fund_asset(setup, test_sdk.get_address(), 1000)
    assert test_sdk.get_address_asset_balance(test_sdk.get_address(), setup.test_asset) == Decimal('1000')


def test_send_asset(setup, test_sdk):
    with pytest.raises(ValueError, match='invalid address'):
        test_sdk.send_asset('bad', setup.test_asset, 10)

    keypair = Keypair.random()
    address = keypair.address().decode()

    with pytest.raises(ValueError, match='amount must be positive'):
        test_sdk.send_asset(address, setup.test_asset, 0)

    with pytest.raises(kin.SdkHorizonError, match=kin.PaymentResultCode.NO_DESTINATION):
        test_sdk.send_asset(address, setup.test_asset, 10)

    tx_hash = test_sdk.create_account(address, starting_balance=100)
    assert tx_hash

    # no trustline yet
    with pytest.raises(kin.SdkHorizonError, match=kin.PaymentResultCode.NO_TRUST):
        test_sdk.send_asset(address, setup.test_asset, 10)

    # add trustline from the newly created account to the kin issuer
    trust_asset(setup, test_sdk, keypair.seed())

    # send asset
    tx_hash = test_sdk.send_asset(address, setup.test_asset, 10.123)
    assert tx_hash
    assert test_sdk.get_address_asset_balance(address, setup.test_asset) == Decimal('10.123')


def test_get_transaction_data(setup, test_sdk):
    with pytest.raises(kin.SdkHorizonError):
        test_sdk.get_transaction_data('bad')

    tx_hash = test_sdk.trust_asset(setup.test_asset, limit=1000)
    assert tx_hash
    sleep(1)
    tx_data = test_sdk.get_transaction_data(tx_hash)
    assert tx_data
    assert tx_data.hash == tx_hash
    assert tx_data.source_account == test_sdk.get_address()
    assert tx_data.created_at
    assert tx_data.source_account_sequence
    assert tx_data.fee_paid == 100
    assert tx_data.memo_type == 'none'
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


def test_get_account_data(setup, test_sdk):
    with pytest.raises(kin.SdkHorizonError):
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


# helpers


def fund(setup, address):
    for attempt in range(3):
        r = requests.get(setup.horizon_endpoint_uri + '/friendbot?addr=' + address)  # Get 10000 lumens
        print('----> ', r.text)
        j = json.loads(r.text)
        if 'hash' in j or 'op_already_exists' in j:
            return
    raise Exception('account funding failed')


def fund_asset(setup, address, amount):
    builder = Builder(secret=setup.issuer_keypair.seed(), horizon=setup.horizon_endpoint_uri, network=setup.network)
    builder.append_payment_op(address, amount, asset_type=setup.test_asset.code, asset_issuer=setup.test_asset.issuer)
    builder.sign()
    reply = builder.submit()
    kin.check_horizon_reply(reply)
    tx_hash = reply.get('hash')
    assert tx_hash


def trust_asset(setup, test_sdk, seed):
    builder = Builder(secret=seed, horizon=test_sdk.horizon.horizon, network=test_sdk.network)
    builder.append_trust_op(setup.test_asset.issuer, setup.test_asset.code)
    builder.sign()
    reply = builder.submit()
    kin.check_horizon_reply(reply)
    tx_hash = reply.get('hash')
    assert tx_hash
