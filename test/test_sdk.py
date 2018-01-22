
from decimal import Decimal
import pytest
from stellar_base.asset import Asset

import kin


@pytest.fixture(scope='session')
def network(testnet):
    class Struct:
        """Handy variable holder"""
        def __init__(self, **entries): self.__dict__.update(entries)

    # if running on stellar testnet, return predefined constants.
    if testnet:
        return Struct(type='testnet')

    return Struct(type='local')


def test_create_fail_empty_endpoint():
    with pytest.raises(kin.SdkConfigurationError, match='cannot connect to horizon'):
        kin.SDK(horizon_endpoint_uri='bad', testnet=True)


def test_create_fail_bad_seed():
    with pytest.raises(TypeError, match='Incorrect padding'):  # TODO: change error?
        kin.SDK(seed='bad', testnet=True)


def test_sdk_not_configured():
    sdk = kin.SDK(testnet=True)
    with pytest.raises(kin.SdkNotConfiguredError, match='address not configured'):
        sdk.get_address()
    with pytest.raises(kin.SdkNotConfiguredError, match='address not configured'):
        sdk.get_lumen_balance()
    with pytest.raises(kin.SdkNotConfiguredError, match='address not configured'):
        sdk.get_kin_balance()
    with pytest.raises(kin.SdkNotConfiguredError, match='address not configured'):
        sdk.create_account('address')
    with pytest.raises(kin.SdkNotConfiguredError, match='address not configured'):
        sdk.trust_asset(Asset('TMP', 'temp'))
    with pytest.raises(kin.SdkNotConfiguredError, match='address not configured'):
        sdk.send_asset('address', Asset('TMP', 'temp'), 1)

