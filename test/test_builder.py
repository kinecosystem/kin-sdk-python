import pytest
import time

from kin.blockchain.builder import Builder
from kin.blockchain.horizon import Horizon
from kin import KinErrors


def test_create_fail():
    with pytest.raises(KinErrors.StellarSecretInvalidError):
        Builder(secret='bad', network_name=None, horizon=None, fee=100)


def test_create():
    seed = 'SASKOJJOG7MLXAWJGE6QNCWH5ZIBH5LWQCXPRGDHUKUOB4RBRWXXFZ2T'
    address = 'GCAZ7QXD6UJ5NOVWYTNKLNP36DPJZMRO67LQ4X5CH2IHY3OG5QGECGYQ'

    # with secret
    builder = Builder(secret=seed, network_name=None, horizon=None, fee=100)
    assert builder
    assert builder.keypair.seed().decode() == seed
    assert builder.address == address


def test_create_custom(test_client):
    seed = 'SASKOJJOG7MLXAWJGE6QNCWH5ZIBH5LWQCXPRGDHUKUOB4RBRWXXFZ2T'
    address = 'GCAZ7QXD6UJ5NOVWYTNKLNP36DPJZMRO67LQ4X5CH2IHY3OG5QGECGYQ'

    horizon = Horizon()
    builder = Builder(secret=seed, horizon=horizon, network_name='custom', fee=100)
    assert builder
    assert builder.horizon
    assert builder.network == 'custom'
    assert builder
    assert builder.horizon == horizon

    # with horizon fixture
    builder = Builder(secret=seed,
                      horizon=test_client.horizon,
                      network_name=test_client.environment.name, fee=100)
    assert builder


@pytest.fixture(scope='session')
def test_builder(test_client, test_account):
    builder = test_account.get_transaction_builder(100)
    return builder


def test_sign(test_builder):
    address = 'GCAZ7QXD6UJ5NOVWYTNKLNP36DPJZMRO67LQ4X5CH2IHY3OG5QGECGYQ'

    test_builder.append_create_account_op(address, '100')
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
    assert test_builder.get_sequence()


def test_update_sequence(test_builder):
    test_builder.update_sequence()
    # TODO: remove str() after kin-base is fixed
    assert test_builder.sequence == str(test_builder.get_sequence())


def test_set_channel(test_client, test_builder):
    channel_addr = 'GBC6PXY4ZSO356NUPF2A2SDVEBQB2RG7XN6337NBW4F24APGHEVR3IIU'
    channel = 'SA4BHY26Q3C3BSYKKGDM7UVMZ4YF6YBLX6AOWYEDBXPLOR7WQ5EJXN6X'
    test_client.friendbot(channel_addr)
    time.sleep(5)
    test_builder.set_channel(channel)
    assert test_builder.address == channel_addr
    assert test_builder.sequence == str(test_builder.get_sequence())


def test_next(test_builder):
    address = 'GCAZ7QXD6UJ5NOVWYTNKLNP36DPJZMRO67LQ4X5CH2IHY3OG5QGECGYQ'

    sequence = test_builder.get_sequence()
    test_builder.append_create_account_op(address, '100')
    test_builder.sign()
    test_builder.next()
    assert not test_builder.tx
    assert not test_builder.te
    assert test_builder.sequence == str(int(sequence) + 1)
