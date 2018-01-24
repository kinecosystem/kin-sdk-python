
from decimal import Decimal
import pytest
from stellar_base.asset import Asset
from stellar_base.keypair import Keypair
from stellar_base.horizon import HORIZON_TEST
from time import sleep
import kin


#TEST_SEED = 'SBOZCCCPGMXZCAE77NE2CFVAF77H5I5CZM6SUEAKMTXRRDP4QCLNDROS'  # GCTAQT4ZHTCAIVDCSI5ZCHPY6LLKWVGBNLF77HVAE2DO6AF3IONLEKRZ
TEST_SEED = 'SAWNYEI5LGSCFIOTMZVND5BDWM7REDOK2TWNBFAQXINLBKYYBUR6A2M7'  # GDQNZRZAU5D5MYSMQX7VNANEVXF6IEIYKAP3TK6WX5HYBV6FGATJ462F
TEST_KEYPAIR = Keypair.from_seed(TEST_SEED)

ISSUER_SEED = 'SCL6VEVYL372VOJ4TYNWF6KMR3MYT3Y4PINC52SXPFNMIHAZKMIEIBWQ'
ISSUER_KEYPAIR = Keypair.from_seed(ISSUER_SEED)

TEST_ASSET = Asset('TEST', ISSUER_KEYPAIR.address().decode())
LOCAL_HORIZON_URI = 'http://localhost:8000'


@pytest.fixture(scope='session')
def network(testnet):
    class Struct:
        """Handy variable holder"""
        def __init__(self, **entries): self.__dict__.update(entries)

    # global testnet
    if testnet:
        return Struct(type='testnet', seed=TEST_SEED)

    # local testnet
    return Struct(type='local', seed=TEST_SEED,horizon_endpoint_uri=HORIZON_TEST)  # LOCAL_HORIZON_URI


def test_sdk_create_fail_bad_endpoint():
    with pytest.raises(kin.SdkConfigurationError, match='cannot connect to horizon'):
        kin.SDK(horizon_endpoint_uri='bad', testnet=True)
    with pytest.raises(kin.SdkConfigurationError, match='cannot connect to horizon'):
        kin.SDK(horizon_endpoint_uri='http://localhost:666', testnet=True)


def test_sdk_create_fail_bad_seed():
    with pytest.raises(TypeError, match='Incorrect padding'):  # TODO: change error
        kin.SDK(seed='bad', testnet=True)


def test_sdk_not_configured():
    sdk = kin.SDK(testnet=True)
    with pytest.raises(kin.SdkNotConfiguredError, match='address not configured'):
        sdk.get_address()
    with pytest.raises(kin.SdkNotConfiguredError, match='address not configured'):
        sdk.get_lumen_balance()
    with pytest.raises(kin.SdkNotConfiguredError, match='address not configured'):
        sdk.get_kin_balance()
    with pytest.raises(kin.SdkNotConfiguredError, match='address not configured'):
        sdk.create_account('address')
    with pytest.raises(kin.SdkNotConfiguredError, match='address not configured'):
        sdk.trust_asset(TEST_ASSET)
    with pytest.raises(kin.SdkNotConfiguredError, match='address not configured'):
        sdk.send_asset('address', TEST_ASSET, 1)


def test_sdk_create_success():
    keypair = Keypair.random()
    sdk = kin.SDK(seed=keypair.seed(), testnet=True)
    assert sdk
    assert sdk.horizon
    assert sdk.network == 'TESTNET'
    assert sdk.keypair.verifying_key == keypair.verifying_key
    assert sdk.keypair.signing_key == keypair.signing_key
    assert sdk.builder


@pytest.fixture(scope='session')
def test_sdk(network):
    sdk = kin.SDK(seed=network.seed, horizon_endpoint_uri=network.horizon_endpoint_uri, testnet=True)
    assert sdk
    return sdk

'''
def test_get_address(test_sdk, network):
    assert test_sdk.get_address() == Keypair.from_seed(network.seed).address().decode()


def test_get_lumen_balance(test_sdk, network):
    assert test_sdk.get_lumen_balance() > 100


def test_get_kin_balance(test_sdk, network):
    # TODO
    pass
    #assert test_sdk.get_lumen_balance() > 100


def test_get_address_lumen_balance(test_sdk):
    address = TEST_KEYPAIR.address().decode()
    assert test_sdk.get_address_lumen_balance(address) > 100
    pass


def test_get_address_kin_balance(test_sdk):
    # TODO
    pass


def test_get_address_asset_balance(test_sdk, network):
    address = TEST_KEYPAIR.address().decode()
    assert test_sdk.get_address_asset_balance(address, Asset('XLM')) > 100
    assert test_sdk.get_address_asset_balance(address, Asset('TMP', 'temp')) == 0


def test_check_account_exists(test_sdk):
    address = TEST_KEYPAIR.address().decode()
    assert test_sdk.check_account_exists(address)


def test_create_account(test_sdk):
    keypair = Keypair.random()
    address = keypair.address().decode()
    starting_balance = 100
    tx_hash = test_sdk.create_account(address, starting_balance=starting_balance)
    assert tx_hash
    assert test_sdk.check_account_exists(address)
    assert test_sdk.get_address_lumen_balance(address) == starting_balance

    # underfunded
    keypair = Keypair.random()
    address = keypair.address().decode()
    with pytest.raises(kin.SdkHorizonError, match=kin.CreateAccountResultCode.UNDERFUNDED):
        test_sdk.create_account(address, starting_balance=1000000)


def test_trust_asset(test_sdk):
    tx_hash = test_sdk.trust_asset(TEST_ASSET, limit=1000)
    assert tx_hash
    assert test_sdk.check_asset_trusted(test_sdk.get_address(), TEST_ASSET)
    # TODO: check limit
'''

def test_get_transaction_data(test_sdk):
    with pytest.raises(kin.SdkHorizonError):
        test_sdk.get_transaction_data('bad')

    tx_hash = test_sdk.trust_asset(TEST_ASSET, limit=1000)
    assert tx_hash
    sleep(1)
    tx_data = test_sdk.get_transaction_data(tx_hash)
    assert tx_data
    print '======== ', tx_data
    assert tx_data.hash == tx_hash
    assert tx_data.source_account == test_sdk.get_address()
    assert tx_data.created_at
    assert len(tx_data.operations) == 1
    op = tx_data.operations[0]
    assert op.id
    assert op.created_at
    assert op.transaction_hash == tx_hash
    assert op.type == 'change_trust'
    assert op.asset_code == TEST_ASSET.code
    assert op.asset_type == 'credit_alphanum4'
    assert op.asset_issuer == TEST_ASSET.issuer
    assert op.trustor == test_sdk.get_address()
    assert op.trustee == TEST_ASSET.issuer
    assert op.limit == Decimal(1000)
    assert op.from_address is None
    assert op.to_address is None
    assert op.amount is None
