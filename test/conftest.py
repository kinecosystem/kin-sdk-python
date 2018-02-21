import json
import pytest
import requests

from stellar_base.asset import Asset
from stellar_base.keypair import Keypair

import kin


def pytest_addoption(parser):
    parser.addoption("--testnet", action="store_true", default=False, help="whether testing on testnet instead of local")


@pytest.fixture(scope='session')
def testnet(request):
    return request.config.getoption("--testnet")


@pytest.fixture(scope='session')
def setup(testnet):
    class Struct:
        """Handy variable holder"""
        def __init__(self, **entries): self.__dict__.update(entries)

    sdk_keypair = Keypair.random()
    issuer_keypair = Keypair.random()
    test_asset = Asset('KIN', issuer_keypair.address().decode())

    # global testnet
    if testnet:
        from stellar_base.horizon import HORIZON_TEST
        return Struct(type='testnet',
                      network='TESTNET',
                      sdk_keypair=sdk_keypair,
                      issuer_keypair=issuer_keypair,
                      test_asset=test_asset,
                      horizon_endpoint_uri=HORIZON_TEST)

    # local testnet (zulucrypto docker)
    # https://github.com/zulucrypto/docker-stellar-integration-test-network
    from stellar_base.network import NETWORKS
    NETWORKS['CUSTOM'] = 'Integration Test Network ; zulucrypto'
    return Struct(type='local',
                  network='CUSTOM',
                  sdk_keypair=sdk_keypair,
                  issuer_keypair=issuer_keypair,
                  test_asset=test_asset,
                  horizon_endpoint_uri='http://localhost:8000')


@pytest.fixture(scope='session')
def test_sdk(setup):
    # create and fund sdk account
    Helpers.fund_account(setup, setup.sdk_keypair.address().decode())

    # create and fund issuer account
    Helpers.fund_account(setup, setup.issuer_keypair.address().decode())

    # init sdk
    sdk = kin.SDK(base_seed=setup.sdk_keypair.seed(), horizon_endpoint_uri=setup.horizon_endpoint_uri, network=setup.network)
    assert sdk

    # override KIN asset with our test asset
    sdk.kin_asset = setup.test_asset

    return sdk


class Helpers:
    """A container for helper functions available to all tests"""
    @staticmethod
    def fund_account(setup, address):
        for attempt in range(3):
            r = requests.get(setup.horizon_endpoint_uri + '/friendbot?addr=' + address)  # Get 10000 lumens
            j = json.loads(r.text)
            if 'hash' in j or 'op_already_exists' in j:
                return
            print('fund error: ', r.text)
        raise Exception('account funding failed')


@pytest.fixture
def helpers():
    return Helpers


