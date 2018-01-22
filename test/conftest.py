import pytest


def pytest_addoption(parser):
    parser.addoption("--testnet", action="store_true", default=False, help="whether testing on testnet instead of local")


@pytest.fixture(scope='session')
def testnet(request):
    return request.config.getoption("--testnet")

