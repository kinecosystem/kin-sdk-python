import pytest

from kin import Environment, KinClient

import logging

logging.basicConfig()


@pytest.fixture(scope='session')
def setup():
    # Set setup values
    class Struct:
        """Handy variable holder"""

        def __init__(self, **entries): self.__dict__.update(entries)

    # Using a local blockchain, this is the root account
    issuer_seed = 'SDBDJVXHPVQGDXYHEVOBBV4XZUDD7IQTXM5XHZRLXRJVY5YMH4YUCNZC'
    issuer_address = 'GCLBBAIDP34M4JACPQJUYNSPZCQK7IRHV7ETKV6U53JPYYUIIVDVJJFQ'
    docker_environment = Environment('DOCKER', 'http://localhost:8008',
                                     'private testnet', issuer_address, 'http://localhost:8001')

    print('Testing with environment:', docker_environment)
    return Struct(issuer_address=issuer_address,
                  issuer_seed=issuer_seed,
                  environment=docker_environment)


@pytest.fixture(scope='session')
def test_client(setup):
    # Create a base KinClient
    print('Created a base KinClient')
    return KinClient(setup.environment)


@pytest.fixture(scope='session')
def test_account(setup, test_client):
    # Create and fund the sdk account from the root account

    sdk_address = 'GAIDUTTQ5UIZDW7VZ2S3ZAFLY6LCRT5ZVHF5X3HDJVDQ4OJWYGJVJDZB'
    sdk_seed = 'SBKI7MEF62NHHH3AOXBHII46K2FD3LVH63FYHUDLTBUYT3II6RAFLZ7B'

    root_account = test_client.kin_account(setup.issuer_seed)
    root_account.create_account(sdk_address, 10000)
    print('Created the base kin account')
    root_account.send_kin(sdk_address, 1000000)
    print('Funded the base kin account')
    return test_client.kin_account(sdk_seed)
