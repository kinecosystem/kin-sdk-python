# -*- coding: utf-8 -*

# Copyright (C) 2018 Kin Foundation

from stellar_base.utils import decode_check


def validate_address(address):
    if len(address) != 56:
        raise ValueError('invalid address')

    try:
        decode_check('account', address)
    except Exception:
        raise ValueError('invalid address')


def validate_secret_key(key):
    if len(key) != 56:
        raise ValueError('invalid secret key')

    try:
        decode_check('seed', key)
    except Exception:
        raise ValueError('invalid secret key')
