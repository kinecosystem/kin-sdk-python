import pytest

from kin.blockchain.builder import Builder
from kin.blockchain.horizon import Horizon


def test_create_fail():
    with pytest.raises(Exception, match='invalid secret key'):
        Builder(secret='bad', network=None, horizon=None, fee=100)
    with pytest.raises(Exception, match='invalid address'):
        Builder(address='bad', network=None, horizon=None, fee=100)


def test_create():
    seed = 'SASKOJJOG7MLXAWJGE6QNCWH5ZIBH5LWQCXPRGDHUKUOB4RBRWXXFZ2T'
    address = 'GCAZ7QXD6UJ5NOVWYTNKLNP36DPJZMRO67LQ4X5CH2IHY3OG5QGECGYQ'

    # with secret
    builder = Builder(secret=seed, network=None, horizon=None, fee=100)
    assert builder
    assert builder.keypair.seed().decode() == seed
    assert builder.address == address

    # with address
    builder = Builder(address=address, network=None, horizon=None, fee=100)
    assert builder
    assert builder.address == address


def test_create_custom(test_client):
    seed = 'SASKOJJOG7MLXAWJGE6QNCWH5ZIBH5LWQCXPRGDHUKUOB4RBRWXXFZ2T'
    address = 'GCAZ7QXD6UJ5NOVWYTNKLNP36DPJZMRO67LQ4X5CH2IHY3OG5QGECGYQ'

    horizon = Horizon()
    builder = Builder(secret=seed, horizon=horizon, network='custom', fee=100)
    assert builder
    assert builder.horizon
    assert builder.network == 'custom'
    assert builder
    assert builder.horizon == horizon

    # with horizon fixture
    builder = Builder(secret=seed,
                      horizon=test_client.horizon,
                      network=test_client.environment.name, fee=100)
    assert builder


@pytest.fixture(scope='session')
def test_builder(test_client, test_account):
    builder = Builder(secret=test_account.keypair.secret_seed,
                      horizon=test_account.horizon,
                      network=test_client.environment.name, fee=100)
    assert builder
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


def test_next(test_builder):
    address = 'GCAZ7QXD6UJ5NOVWYTNKLNP36DPJZMRO67LQ4X5CH2IHY3OG5QGECGYQ'

    sequence = test_builder.get_sequence()
    test_builder.append_create_account_op(address, '100')
    test_builder.sign()
    test_builder.next()
    assert not test_builder.tx
    assert not test_builder.te
    assert test_builder.sequence == str(int(sequence) + 1)
