import pytest

from stellar.utils import validate_address, validate_secret_key


def test_validate_address():
    with pytest.raises(ValueError, match='invalid address'):
        validate_address('bad')
    with pytest.raises(ValueError, match='invalid address'):
        validate_address('deadbeefdeadbeefdeadbeefdeadbeefdeadbeefdeadbeefdeadbeef')
    address = 'GDQNZRZAU5D5MYSMQX7VNANEVXF6IEIYKAP3TK6WX5HYBV6FGATJ462F'
    with pytest.raises(ValueError, match='invalid address'):
        validate_address(address.replace('M', 'N'))
    validate_address(address)


def test_validate_secret_key():
    with pytest.raises(ValueError, match='invalid secret key'):
        validate_secret_key('bad')
    with pytest.raises(ValueError, match='invalid secret key'):
        validate_secret_key('deadbeefdeadbeefdeadbeefdeadbeefdeadbeefdeadbeefdeadbeef')
    key = 'SBQBGUY2RKHDTW4QYH6366QO2U7BHY7F6HFMA42VQIM6QN5X7BGUIRS5'
    with pytest.raises(ValueError, match='invalid secret key'):
        validate_secret_key(key.replace('M', 'N'))
    validate_secret_key(key)

