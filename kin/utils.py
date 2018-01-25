# -*- coding: utf-8 -*

# Copyright (C) 2018 Kin Foundation


from stellar_base.utils import decode_check
from .exceptions import SdkHorizonError


def validate_address(address):
    if len(address) != 56:
        raise ValueError('invalid address')

    decoded = decode_check('account', address)
    if len(decoded) != 32:
        raise ValueError('invalid address')


def check_horizon_reply(reply):
    if 'status' not in reply:
        return reply
    raise SdkHorizonError(reply)
