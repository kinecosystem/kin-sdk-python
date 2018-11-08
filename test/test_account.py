import pytest
from kin import KinErrors
from kin import Keypair
from kin.config import MEMO_TEMPLATE, ANON_APP_ID
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

    with pytest.raises(KinErrors.StellarSecretInvalidError):
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
        assert test_client.does_account_exists(Keypair.address_from_seed(channel))


def test_get_address(test_client, test_account):
    assert test_account.get_public_address() == SDK_PUBLIC


def test_create_account(test_client, test_account):
    with pytest.raises(KinErrors.AccountExistsError):
        test_account.create_account(test_client.kin_asset.issuer, 0, fee=100)

    test_account.create_account('GDN7KB72OO7G6VBD3CXNRFXVELLW6F36PS42N7ASZHODV7Q5GYPETQ74', 0, fee=100)
    assert test_client.does_account_exists('GDN7KB72OO7G6VBD3CXNRFXVELLW6F36PS42N7ASZHODV7Q5GYPETQ74')


def test_send_kin(test_client, test_account):
    recipient = 'GBZWWLRJRWL4DLYOJMCHXJUOJJY5NLNJHQDRQHVQH43KFCPC3LEOWPYM'
    test_client.friendbot(recipient)

    test_account.send_kin(recipient, 10, fee=100)
    balance = test_client.get_account_balance(recipient)
    assert balance == 10


def test_build_create_account(test_account):
    recipient = 'GBZWWLRJRWL4DLYOJMCHXJUOJJY5NLNJHQDRQHVQH43KFCPC3LEOWPYM'
    with pytest.raises(KinErrors.StellarSecretInvalidError):
        test_account.build_create_account('bad address', 0, fee=100)
    with pytest.raises(KinErrors.NotValidParamError):
        test_account.build_create_account(recipient, 0, memo_text='a' * 50 ,fee=100)
    with pytest.raises(ValueError):
        test_account.build_create_account(recipient, -1, fee=100)

    tx = test_account.build_create_account(recipient, 0, starting_balance=10, fee=100)

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
    with pytest.raises(KinErrors.StellarAddressInvalidError):
        test_account.build_send_kin('bad address', 0, fee=100)
    with pytest.raises(KinErrors.NotValidParamError):
        test_account.build_send_kin(recipient, 10, memo_text='a' * 50, fee=100)
    with pytest.raises(ValueError):
        test_account.build_send_kin(recipient, -50, fee=100)
    with pytest.raises(KinErrors.NotValidParamError):
        test_account.build_send_kin(recipient, 1.1234567898765, fee=100)

    tx = test_account.build_send_kin(recipient, 10, fee=100)

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
    test_account.create_account(public, 0, fee=100)

    account = test_client.kin_account(test_account.keypair.secret_seed, channel_secret_keys=[channel])
    account.send_kin(public, 10, fee=100)

    channel_balance = test_client.get_account_balance(public)
    # channel should have ran out of funds, so the base account should have topped it up
    assert channel_balance > 0


def test_memo(test_client, test_account):
    recipient1 = 'GCT3YLKNVEILHUOZYK3QPOVZWWVLF5AE5D24Y6I4VH7WGZYBFU2HSXYX'
    recipient2 = 'GDR375ZLWHZUFH2SWXFEH7WVPK5G3EQBLXPZKYEFJ5EAW4WE4WIQ5BP3'

    tx1 = test_account.create_account(recipient1, 0, memo_text='Hello', fee=100)
    account2 = test_client.kin_account(test_account.keypair.secret_seed, app_id='test', fee=100)
    tx2 = account2.create_account(recipient2, 0, memo_text='Hello', fee=100)
    sleep(5)

    tx1_data = test_client.get_transaction_data(tx1)
    tx2_data = test_client.get_transaction_data(tx2)

    assert tx1_data.memo == MEMO_TEMPLATE.format(ANON_APP_ID) + 'Hello'
    assert tx2_data.memo == MEMO_TEMPLATE.format('test') + 'Hello'

    with pytest.raises(KinErrors.NotValidParamError):
        account2.create_account(recipient2, 0, memo_text='a'*25, fee=100)

