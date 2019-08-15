import pytest
from time import sleep

from kin import KinClient, TEST_ENVIRONMENT, KinErrors
from kin import config, client


def test_create():
    client = KinClient(TEST_ENVIRONMENT)
    assert client
    assert client.environment == TEST_ENVIRONMENT
    assert client.horizon
    assert client.network == TEST_ENVIRONMENT.name


@pytest.mark.asyncio
async def test_get_minimum_fee(test_client):
    assert await test_client.get_minimum_fee() == 100


@pytest.mark.asyncio
async def test_get_config(setup, test_client):
    from kin import Environment
    # bad Horizon endpoint
    env = Environment('bad', 'bad', 'bad', 'GDZA33STWFOVWLHAFXEOYS46DA2VMIQH3MCCVVGAUENMZMMZJFAHT4KO')
    status = await KinClient(env).get_config()
    assert status['horizon']
    assert status['horizon']['online'] is False
    assert 'InvalidURL' in status['horizon']['error']

    # no Horizon on endpoint
    env = Environment('bad', 'http://localhost:666', 'bad', 'GDZA33STWFOVWLHAFXEOYS46DA2VMIQH3MCCVVGAUENMZMMZJFAHT4KO')
    status = await KinClient(env).get_config()
    assert status['horizon']
    assert status['horizon']['online'] is False
    assert 'ClientConnectorError' in status['horizon']['error']

    # success
    status = await test_client.get_config()
    assert status['environment'] == setup.environment.name
    assert status['horizon']
    assert status['horizon']['uri'] == setup.environment.horizon_uri
    assert status['horizon']['online']
    assert status['horizon']['error'] is None
    assert status['transport']
    assert status['transport']['pool_size']
    assert status['transport']['num_retries']
    assert status['transport']['request_timeout']
    assert status['transport']['backoff_factor']


@pytest.mark.asyncio
async def test_get_balance(test_client, test_account):
    balance = await test_client.get_account_balance(test_account.get_public_address())
    assert balance > 0


@pytest.mark.asyncio
async def test_does_account_exists(test_client, test_account):

    with pytest.raises(KinErrors.StellarAddressInvalidError):
        await test_client.does_account_exists('bad')

    address = 'GB7F23F7235ADJ7T2L4LJZT46LA3256QAXIU56ANKPX5LSAAS3XVA465'
    assert not await test_client.does_account_exists(address)
    assert await test_client.does_account_exists(test_account.get_public_address())


@pytest.mark.asyncio
async def test_get_account_data(test_client, test_account):
    with pytest.raises(KinErrors.StellarAddressInvalidError):
        await test_client.get_account_data('bad')

    address = 'GBSZO2C63WM2DHAH4XGCXDW5VGAM56FBIOGO2KFRSJYP5I4GGCPAVKHW'
    with pytest.raises(KinErrors.AccountNotFoundError):
        await test_client.get_account_data(address)

    acc_data = await test_client.get_account_data(test_account.get_public_address())
    assert acc_data
    assert acc_data.id == test_account.get_public_address()
    assert acc_data.sequence
    assert acc_data.data == {}

    assert acc_data.thresholds
    assert acc_data.thresholds.low_threshold == 0
    assert acc_data.thresholds.med_threshold == 0
    assert acc_data.thresholds.high_threshold == 0

    assert acc_data.flags
    assert not acc_data.flags.auth_revocable
    assert not acc_data.flags.auth_required

    assert len(acc_data.balances) == 1
    native_balance = acc_data.balances[0]
    assert native_balance.balance > 0
    assert native_balance.asset_type == 'native'

    # just to increase test coverage
    assert str(acc_data)


@pytest.mark.asyncio
async def test_get_transaction_data(setup, test_client):
    from kin import OperationTypes
    from kin.transactions import RawTransaction

    with pytest.raises(ValueError):
        await test_client.get_transaction_data('bad')

    with pytest.raises(KinErrors.ResourceNotFoundError):
        await test_client.get_transaction_data('deadbeefdeadbeefdeadbeefdeadbeefdeadbeefdeadbeefdeadbeefdeadbeef')

    address = 'GAHTWFVYV4RF2AMEZP3X2VOK4HB3YOSARU7VNVTP7J2OLDSVOP564YEN'
    tx_hash = await test_client.friendbot(address)
    sleep(5)
    tx_data = await test_client.get_transaction_data(tx_hash)
    assert tx_data
    assert tx_data.id == tx_hash
    assert tx_data.timestamp
    assert tx_data.memo is None
    assert tx_data.operation
    assert tx_data.source == setup.issuer_address  # root account
    assert tx_data.operation.type == OperationTypes.CREATE_ACCOUNT
    assert tx_data.operation.destination == address
    assert tx_data.operation.starting_balance == 0

    tx_data = await test_client.get_transaction_data(tx_hash, simple=False)
    assert isinstance(tx_data, RawTransaction)


@pytest.mark.asyncio
async def test_friendbot(test_client):
    address = 'GDIPKVWPVCL5E5MX4UWMLCGXMDWEMEYAZGCI3TPJPVDG5ZFA6VJAA7RA'
    await test_client.friendbot(address)
    assert await test_client.does_account_exists(address)

    with pytest.raises(KinErrors.StellarAddressInvalidError):
        await test_client.friendbot('bad')


@pytest.mark.skip('Our friendbot is configured with 0 starting balance, '
                  'currently the friendbot uses the starting balance to determine the limit fo the fund amount')
@pytest.mark.asyncio
async def test_friendbot_fund(test_client):
    address = 'GAEVHFWZPWV46AUA5MC6AP4KPOSUOWCFJ2PZCSWFIRXTUKQAKOC3NFPD'
    await test_client.friendbot(address)
    old_balance = await test_client.get_account_balance(address)

    await test_client.friendbot_fund(address, 500)
    new_balance = await test_client.get_account_balance(address)
    assert new_balance == old_balance + 500

    with pytest.raises(ValueError):
        await test_client.friendbot_fund(address, 5000000)

    with pytest.raises(ValueError):
        await test_client.friendbot_fund(address, -500)


@pytest.mark.asyncio
async def test_tx_history(test_client, test_account):
    address = 'GA4GDLBEWVT5IZZ6JKR4BF3B6JJX5S6ISFC2QCC7B6ZVZWJDMR77HYP6'
    await test_client.friendbot(address)
    txs = []
    for _ in range(6):
        txs.append(await test_account.send_kin(address, 1, fee=100))

    # let horizon ingest the txs
    sleep(10)
    tx_history = await test_client.get_account_tx_history(test_account.get_public_address(), amount=6)

    history_ids = [tx.id for tx in tx_history]
    # tx history goes from latest to oldest
    history_ids.reverse()

    assert txs == history_ids

    # test paging
    client.MAX_RECORDS_PER_REQUEST = 4

    tx_history = await test_client.get_account_tx_history(test_account.get_public_address(), amount=6)
    history_ids = [tx.id for tx in tx_history]
    history_ids.reverse()

    assert txs == history_ids


@pytest.mark.asyncio
async def test_client_context(setup):
    async with KinClient(TEST_ENVIRONMENT) as client:
        context_channel = client
        assert not context_channel.horizon._session.closed
    assert context_channel.horizon._session.closed
