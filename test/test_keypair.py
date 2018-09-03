import pytest

from kin import Keypair
from kin.blockchain.utils import is_valid_secret_key


def test_create():
    keys = Keypair()
    assert keys
    assert keys.secret_seed is not None


def test_create_costume():
    seed = 'SCQU5ZUNXUX6I2KKN5FTSFTC5MV5CIOP3VMX6TQG2JBTXHL2BYA7A2A6'
    keys = Keypair(seed)
    assert keys
    assert seed == keys.secret_seed

    with pytest.raises(ValueError):
        Keypair('bad')


def test_generate_seed():
    seed = Keypair.generate_seed()
    assert is_valid_secret_key(seed)


def test_address_from_seed():
    seed = 'SALUL77R6UREW7KEUPO4YJL53JLZQXZQI5TTJ5RIWAANGOEDQNPQX53B'
    address = Keypair.address_from_seed(seed)
    assert address == 'GDZA33STWFOVWLHAFXEOYS46DA2VMIQH3MCCVVGAUENMZMMZJFAHT4KO'


def test_hd_seed():
    base_seed = 'SALUL77R6UREW7KEUPO4YJL53JLZQXZQI5TTJ5RIWAANGOEDQNPQX53B'
    hd_seeds = [
        'SAMOP5WPLANJO6EDGPHHWQHZLGWF64YBSPSJGRWNQJHDC66LPXWDJFE6',
        'SAEKXALOS3KKJLLPWNW2TBD2WKX6DMUYPVDSVJ6T7S2H5TR52OICJVJZ',
        'SDIFS2MZF6E3BC2LX3OA7M6L4KJOOQBZ6VZ3W2HEFGFNP2GYZB4NUPJL',
        'SDEE4X6JXBKCYFZJH6PLT633OO6FWVEQWV4RKI2HA5BENJAWCCRM6AY4'
    ]

    for i in range(4):
        assert Keypair.generate_hd_seed(base_seed,str(i)) == hd_seeds[i]