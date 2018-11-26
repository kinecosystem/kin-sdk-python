import pytest

from kin.blockchain.utils import *
from kin.utils import get_hd_channels, create_channels


def test_is_valid_address():
    assert not is_valid_address('bad')
    assert not is_valid_address('deadbeefdeadbeefdeadbeefdeadbeefdeadbeefdeadbeefdeadbeef')
    address = 'GDQNZRZAU5D5MYSMQX7VNANEVXF6IEIYKAP3TK6WX5HYBV6FGATJ462F'
    assert not is_valid_address(address.replace('M', 'N'))
    assert is_valid_address(address)


def test_is_valid_secret_key():
    assert not is_valid_secret_key('bad')
    assert not is_valid_secret_key('deadbeefdeadbeefdeadbeefdeadbeefdeadbeefdeadbeefdeadbeef')
    key = 'SBQBGUY2RKHDTW4QYH6366QO2U7BHY7F6HFMA42VQIM6QN5X7BGUIRS5'
    assert not is_valid_secret_key(key.replace('M', 'N'))
    assert is_valid_secret_key(key)


def test_is_valid_transaction_hash():
    assert not is_valid_transaction_hash('bad')
    assert is_valid_transaction_hash('c2a9d905a728ae918bf50058548f2421463ae09e1302be8e5b4b882c81c2edb8')


def test_get_hd_channels():
    channels = ['SCIM75YWRIU7G7B5JECYT44NQZDCL4IOQ7CXBWAQLMXQDTRVMNJMLXBA',
                'SCA7Q4TB6QJZQQPTKHBSICPNJELIXSE66Z57ZAKWCZOBIQUXJLQVDW4W',
                'SAG3ERPST7DW5FVSZN24QMFFHGSNPT7RRWCU4T4NX5LBBAE2BBNJNOKG',
                'SBUDIZMRGW32OBWLM6BYU3QPF5ZSWT5YO6TX4Q3CWKLE6PFAMFQPCT43']

    assert set(get_hd_channels('SC6WVXYFXJKG3SLAOYKZAPTQI5ZDKZ3JQNBZMCRZK4ZM3HYIRGRSBDPA','hello',4)) == set(channels)


