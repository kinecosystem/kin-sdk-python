"""Contains useful methods to be used across the sdk"""

from kin_base.utils import decode_check


def is_valid_address(address):
    """Determines if the provided string is a valid Stellar address.

    :param str address: address to check

    :return: True if this is a correct address
    :rtype: boolean
    """
    if len(address) != 56:
        return False

    try:
        decode_check('account', address)
        return True
    except:
        return False


def is_valid_secret_key(key):
    """Determines if the provided string is a valid Stellar key (seed).

    :param str key: key to check

    :return: True if this is a correct seed
    :rtype: boolean
    """
    if len(key) != 56:
        return False

    try:
        decode_check('seed', key)
        return True
    except:
        return False


def is_valid_transaction_hash(tx_hash):
    """Determines if the provided string is a valid Stellar transaction hash.

    :param str tx_hash: transaction hash to check

    :return: True if this is a correct transaction hash
    :rtype: boolean
    """
    if len(tx_hash) != 64:
        return False

    try:
        int(tx_hash, 16)
        return True
    except:
        return False
