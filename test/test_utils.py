import pytest

from kin.utils import validate_address, validate_seed


def test_validate_address():
    with pytest.raises(ValueError, match='invalid address'):
        validate_address('bad')
    with pytest.raises(ValueError, match='invalid address'):
        validate_address('deadbeefdeadbeefdeadbeefdeadbeefdeadbeefdeadbeefdeadbeef')
    address = 'GDQNZRZAU5D5MYSMQX7VNANEVXF6IEIYKAP3TK6WX5HYBV6FGATJ462F'
    with pytest.raises(ValueError, match='invalid address'):
        validate_address(address.replace('M', 'N'))
    validate_address(address)


def test_validate_seed():
    with pytest.raises(ValueError, match='invalid seed'):
        validate_seed('bad')
    with pytest.raises(ValueError, match='invalid seed'):
        validate_seed('deadbeefdeadbeefdeadbeefdeadbeefdeadbeefdeadbeefdeadbeef')
    seed = 'SBQBGUY2RKHDTW4QYH6366QO2U7BHY7F6HFMA42VQIM6QN5X7BGUIRS5'
    with pytest.raises(ValueError, match='invalid seed'):
        validate_seed(seed.replace('M', 'N'))
    validate_seed(seed)

