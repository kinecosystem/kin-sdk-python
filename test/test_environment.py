from hashlib import sha256

import pytest
from kin import Environment


def test_create_success():
    passphrase = 'passphrase'
    passphrase_hash = sha256(passphrase.encode()).digest()

    env = Environment('test', 'http://horizon.com', passphrase)

    assert env.name == 'TEST'
    assert env.horizon_uri == 'http://horizon.com'
    assert passphrase_hash == env.passphrase_hash
