# -*- coding: utf-8 -*

# Copyright (C) 2018 Kin Foundation


from stellar_base.utils import decode_check


def validate_address(address):
    if len(address) != 56:
        return False
    try:
        decoded = decode_check('account', address)
        if len(decoded) != 32:
            return False
    except:
        return False

    return True

