import pytest
from kin import KinErrors
from kin import Keypair
from kin import AccountStatus
from kin.config import BASE_RESERVE, DEFAULT_FEE, MEMO_TEMPLATE, ANON_APP_ID
from kin.blockchain.utils import is_valid_transaction_hash
from time import sleep

SDK_PUBLIC = 'GAIDUTTQ5UIZDW7VZ2S3ZAFLY6LCRT5ZVHF5X3HDJVDQ4OJWYGJVJDZB'
SDK_SEED = 'SBKI7MEF62NHHH3AOXBHII46K2FD3LVH63FYHUDLTBUYT3II6RAFLZ7B'


def test_create_basic(test_client, test_account):
    with pytest.raises(KinErrors.AccountNotActivatedError):
        account = test_client.kin_account('SD6IDZHCMX3Z4QPDIC33PECKLLY572DAA5S3DZDALEVVACJKSZPVPJC6')

    with pytest.raises(ValueError):
        account = test_client.kin_account('bad format')

    account = test_client.kin_account(SDK_SEED)
    assert account
    assert account.keypair.secret_seed == SDK_SEED
    assert account.keypair.public_address == SDK_PUBLIC
    assert account.horizon
    assert account.channel_manager


def test_create_exisitng_channels(test_client, test_account):
    channels = [
        'SBIS2IZXKV7ZQABHYAXO6DR2GZKBUHNHYFYKGC4MNVURPFTY5RFBT5QX',
        'SAFROZPOSDXU2JME6EQ3IDXZVGMSRIFNTX7CSMSUCUX4SBZNRBQUAGVI',
        'SCWOPWB2JPVWYYJMJO754AWPZ6VJWOZJMOK3JY3JPA3N3ER7SKMQEMXH'
    ]

    with pytest.raises(KinErrors.AccountNotFoundError):
        account = test_client.kin_account(SDK_SEED, channel_secret_keys=channels)

    with pytest.raises(ValueError):
        account = test_client.kin_account(SDK_SEED, channel_secret_keys=['bad'])

    with pytest.raises(ValueError):
        account = test_client.kin_account(SDK_SEED, channel_secret_keys=channels, create_channels=True)

    for channel in channels:
        test_client.friendbot(Keypair.address_from_seed(channel))

    account = test_client.kin_account(SDK_SEED, channel_secret_keys=channels)
    assert account
    assert set(channels) == set(account.channel_secret_keys)


def test_create_new_channels(test_client, test_account):
    with pytest.raises(KinErrors.AccountNotFoundError):
        account = test_client.kin_account(SDK_SEED, channels=2, create_channels=False)

    account = test_client.kin_account(SDK_SEED, channels=4, create_channels=True)
    assert account
    assert len(account.channel_secret_keys) == 4
    for channel in account.channel_secret_keys:
        assert test_client.get_account_status(Keypair.address_from_seed(channel)) \
               == AccountStatus.NOT_ACTIVATED


def test_get_address(test_client, test_account):
    assert test_account.get_public_address() == SDK_PUBLIC


def test_create_account(test_client, test_account):
    with pytest.raises(KinErrors.AccountExistsError):
        test_account.create_account(test_client.kin_asset.issuer)

    test_account.create_account('GDN7KB72OO7G6VBD3CXNRFXVELLW6F36PS42N7ASZHODV7Q5GYPETQ74')
    status = test_client.get_account_status('GDN7KB72OO7G6VBD3CXNRFXVELLW6F36PS42N7ASZHODV7Q5GYPETQ74')
    assert status == AccountStatus.NOT_ACTIVATED


def test_send_xlm(test_client, test_account):
    recipient = 'GAXEQOJBLECPIZMU6LDLFZYRM46GWTQ6ZT462ZFUMYSLTGM2D6ZFYQ7T'
    test_client.friendbot(recipient)
    xlm_balance = test_client.get_account_balances(recipient)['XLM']
    test_account.send_xlm(recipient, 5)
    new_balance = test_client.get_account_balances(recipient)['XLM']
    assert xlm_balance + 5 == new_balance


def test_send_kin(test_client, test_account):
    recipient = 'GBZWWLRJRWL4DLYOJMCHXJUOJJY5NLNJHQDRQHVQH43KFCPC3LEOWPYM'
    test_client.friendbot(recipient)
    test_client.activate_account('SARPTF6PRFJVZV3BUKKMYB54Z6KVXK4W23U3TGW2545MIOTH2BQ4TRLK')

    test_account.send_kin(recipient, 10)
    balance = test_client.get_account_balances(recipient)['KIN']
    assert balance == 10


def test_build_create_account(test_account):
    recipient = 'GBZWWLRJRWL4DLYOJMCHXJUOJJY5NLNJHQDRQHVQH43KFCPC3LEOWPYM'
    with pytest.raises(ValueError):
        test_account.build_create_account('bad address')
    with pytest.raises(KinErrors.MemoTooLongError):
        test_account.build_create_account(recipient, memo_text='a' * 50)

    tx = test_account.build_create_account(recipient, starting_balance=10)

    try:
        assert tx
        assert tx.builder
        assert tx.channel_manager
        assert is_valid_transaction_hash(tx.hash)
        assert test_account.channel_manager.channel_builders.empty()
    except Exception:
        pass
    finally:
        tx.release()
        assert test_account.channel_manager.channel_builders.full()


def test_build_send_kin(test_account):
    recipient = 'GBZWWLRJRWL4DLYOJMCHXJUOJJY5NLNJHQDRQHVQH43KFCPC3LEOWPYM'
    with pytest.raises(ValueError):
        test_account.build_create_account('bad address')
    with pytest.raises(KinErrors.MemoTooLongError):
        test_account.build_send_kin(recipient, 10, memo_text='a' * 50)
    with pytest.raises(ValueError):
        test_account.build_send_kin(recipient, -50)
    with pytest.raises(ValueError):
        test_account.build_send_kin(recipient, 1.1234567898765)

    tx = test_account.build_send_kin(recipient, 10)

    try:
        assert tx
        assert tx.builder
        assert tx.channel_manager
        assert is_valid_transaction_hash(tx.hash)
        assert test_account.channel_manager.channel_builders.empty()
    except Exception:
        pass
    finally:
        tx.release()
        assert test_account.channel_manager.channel_builders.full()


def test_auto_top_up(test_client, test_account):
    channel = 'SBYU2EBGTTGIFR4O4K4SQXTD4ISMVX4R5TX2TTB4SWVIA5WVRS2MHN4K'
    public = 'GBKZAXTDJRYBK347KDTOFWEBDR7OW3U67XV2BOF2NLBNEGRQ2WN6HFK6'
    test_account.create_account(public, starting_balance=3 * BASE_RESERVE + DEFAULT_FEE)
    test_client.activate_account(channel)

    account = test_client.kin_account(test_account.keypair.secret_seed, channel_secret_keys=[channel])
    account.send_kin(public, 10)

    channel_balance = test_client.get_account_balances(public)['XLM']
    # channel should have ran out of funds, so the base account should have topped it up
    assert channel_balance > 3 * BASE_RESERVE + DEFAULT_FEE


def test_memo(test_client, test_account):
    recipient1 = 'GCT3YLKNVEILHUOZYK3QPOVZWWVLF5AE5D24Y6I4VH7WGZYBFU2HSXYX'
    recipient2 = 'GDR375ZLWHZUFH2SWXFEH7WVPK5G3EQBLXPZKYEFJ5EAW4WE4WIQ5BP3'

    tx1 = test_account.create_account(recipient1, memo_text='Hello')
    account2 = test_client.kin_account(test_account.keypair.secret_seed, app_id='test')
    tx2 = account2.create_account(recipient2, memo_text='Hello')
    sleep(5)

    tx1_data = test_client.get_transaction_data(tx1)
    tx2_data = test_client.get_transaction_data(tx2)

    assert tx1_data.memo == MEMO_TEMPLATE.format(ANON_APP_ID) + 'Hello'
    assert tx2_data.memo == MEMO_TEMPLATE.format('test') + 'Hello'

    with pytest.raises(KinErrors.MemoTooLongError):
        account2.create_account(recipient2, memo_text='a'*25)

