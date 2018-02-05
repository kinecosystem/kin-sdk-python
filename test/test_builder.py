import pytest

from stellar_base.keypair import Keypair
from kin.builder import Builder
from kin.horizon import Horizon, HORIZON_LIVE, HORIZON_TEST


def test_create_fail():
    with pytest.raises(Exception, match='either secret or address must be provided'):
        Builder()
    with pytest.raises(Exception, match='invalid seed'):
        Builder(secret='bad')
    with pytest.raises(Exception, match='invalid address'):
        Builder(address='bad')


def test_create_default():
    keypair = Keypair.random()

    # with secret
    builder = Builder(secret=keypair.seed())
    assert builder
    assert builder.key_pair.seed() == keypair.seed()
    assert builder.address == keypair.address().decode()
    assert builder.network == 'PUBLIC'
    assert builder.horizon
    assert builder.horizon.horizon_uri == HORIZON_LIVE
    assert builder.sequence == builder.get_sequence()

    # with address
    builder = Builder(address=keypair.address().decode())
    assert builder
    assert builder.address == keypair.address().decode()
    assert builder.network == 'PUBLIC'
    assert builder.horizon
    assert builder.horizon.horizon_uri == HORIZON_LIVE
    assert builder.sequence == builder.get_sequence()

    # on testnet
    builder = Builder(secret=keypair.seed(), network='TESTNET')
    assert builder
    assert builder.network == 'TESTNET'
    assert builder.horizon
    assert builder.horizon.horizon_uri == HORIZON_TEST


def test_create_custom():
    keypair = Keypair.random()

    builder = Builder(secret=keypair.seed(), horizon_uri='custom', network='custom', sequence=7)
    assert builder
    assert builder.horizon
    assert builder.horizon.horizon_uri == 'custom'
    assert builder.network == 'CUSTOM'
    assert builder.sequence == 7

    # with custom horizon
    horizon = Horizon()
    builder = Builder(secret=keypair.seed(), horizon=horizon)
    assert builder
    assert builder.horizon == horizon


def test_clear(test_sdk):
    builder = Builder(secret=test_sdk.base_keypair.seed(), horizon=test_sdk.horizon, network=test_sdk.network)
    builder.append_create_account_op(Keypair.random().address().decode(), 100)
    builder.sign()
    assert len(builder.ops) == 1
    assert builder.te
    assert builder.tx

    builder.clear()
    assert len(builder.ops) == 0
    assert not builder.te
    assert not builder.tx
