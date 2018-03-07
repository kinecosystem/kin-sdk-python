# -*- coding: utf-8 -*

# Copyright (C) 2018 Kin Foundation

from stellar_base.utils import decode_check


def is_valid_address(address):
    if len(address) != 56:
        return False

    try:
        decode_check('account', address)
        return True
    except:
        return False


def is_valid_secret_key(key):
    if len(key) != 56:
        return False

    try:
        decode_check('seed', key)
        return True
    except:
        return False


def is_valid_transaction_hash(tx_hash):
    if len(tx_hash) != 64:
        return False

    try:
        int(tx_hash, 16)
        return True
    except:
        return False
