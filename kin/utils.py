# -*- coding: utf-8 -*

# Copyright (C) 2018 Kin Foundation

from stellar_base.utils import decode_check


def validate_address(address):
    if len(address) != 56:
        raise ValueError('invalid address')

    try:
        decoded = decode_check('account', address)
    except Exception:
        raise ValueError('invalid address')

    if len(decoded) != 32:
        raise ValueError('invalid address')


def validate_seed(seed):
    if len(seed) != 56:
        raise ValueError('invalid seed')

    try:
        decoded = decode_check('seed', seed)
    except Exception:
        raise ValueError('invalid seed')

    if len(decoded) != 32:
        raise ValueError('invalid seed')

