import pytest

from stellar_base.keypair import Keypair
from kin.stellar.builder import Builder
from kin.stellar.horizon import Horizon, HORIZON_LIVE, HORIZON_TEST


def test_create_fail():
    with pytest.raises(Exception, match='either secret or address must be provided'):
        Builder()
    with pytest.raises(Exception, match='invalid secret key'):
        Builder(secret='bad')
    with pytest.raises(Exception, match='invalid address'):
        Builder(address='bad')


def test_create_default():
    keypair = Keypair.random()

    # with secret
    builder = Builder(secret=keypair.seed(), sequence=7)
    assert builder
    assert builder.key_pair.seed() == keypair.seed()
    assert builder.address == keypair.address().decode()
    assert builder.network == 'PUBLIC'
    assert builder.horizon
    assert builder.horizon.horizon_uri == HORIZON_LIVE
    assert builder.sequence == 7

    # with address
    builder = Builder(address=keypair.address().decode(), sequence=7)
    assert builder
    assert builder.address == keypair.address().decode()
    assert builder.network == 'PUBLIC'
    assert builder.horizon
    assert builder.horizon.horizon_uri == HORIZON_LIVE
    assert builder.sequence == 7

    # on testnet
    builder = Builder(secret=keypair.seed(), network='TESTNET', sequence=7)
    assert builder
    assert builder.network == 'TESTNET'
    assert builder.horizon
    assert builder.horizon.horizon_uri == HORIZON_TEST


def test_create_custom(test_sdk):
    keypair = Keypair.random()

    builder = Builder(secret=keypair.seed(), horizon_uri='custom', network='custom', sequence=7)
    assert builder
    assert builder.horizon
    assert builder.horizon.horizon_uri == 'custom'
    assert builder.network == 'CUSTOM'
    assert builder.sequence == 7

    # with custom horizon
    horizon = Horizon()
    builder = Builder(secret=keypair.seed(), horizon=horizon, sequence=7)
    assert builder
    assert builder.horizon == horizon

    # with horizon fixture
    builder = Builder(secret=test_sdk.base_keypair.seed(), horizon=test_sdk.horizon, network=test_sdk.network)
    assert builder
    assert builder.sequence == builder.get_sequence()


@pytest.fixture(scope='session')
def test_builder(test_sdk):
    builder = Builder(secret=test_sdk.base_keypair.seed(), horizon=test_sdk.horizon, network=test_sdk.network)
    assert builder
    return builder


def test_sign(test_builder):
    test_builder.append_create_account_op(Keypair.random().address().decode(), 100)
    assert len(test_builder.ops) == 1
    test_builder.sign()
    assert test_builder.te
    assert test_builder.tx


def test_clear(test_builder):
    test_builder.clear()
    assert len(test_builder.ops) == 0
    assert not test_builder.te
    assert not test_builder.tx


def test_get_sequence(test_builder):
    assert test_builder.sequence == test_builder.get_sequence()


def test_next(test_builder):
    sequence = test_builder.sequence
    test_builder.append_create_account_op(Keypair.random().address().decode(), 100)
    test_builder.sign()
    test_builder.next()
    assert not test_builder.tx
    assert not test_builder.te
    assert test_builder.sequence == str(int(sequence) + 1)

