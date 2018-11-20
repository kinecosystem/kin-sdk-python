import pytest
from time import sleep


def test_single_monitor(test_client, test_account):
    address = 'GCFNA3MUPL6ZELRZQD5IGBZRWMYIQV6VVG2LCAERLY2A7W5VVRXSBH75'
    seed = 'SAEAU66JLC5QNKSNABHH56XXKLHVSQAK7RH34VD2LEALNDKRBLSZ66QD'
    test_client.friendbot(address)

    txs_found = []

    def account_tx_callback(addr, tx_data, monitor):
        assert addr == address
        txs_found.append(tx_data.id)

    # start monitoring
    monitor = test_client.monitor_account_payments(address, account_tx_callback)
    assert monitor.thread.is_alive()

    # pay from sdk to the account
    hash1 = test_account.send_kin(address, 1, fee=100)
    hash2 = test_account.send_kin(address, 2, fee=100)
    sleep(20)

    # Horizon should timeout after 10 seconds of no traffic, make sure we reconnected
    hash3 = test_account.send_kin(address, 3, fee=100)

    sleep(5)
    assert hash1 in txs_found
    assert hash2 in txs_found
    assert hash3 in txs_found

    monitor.stop()
    # Make sure we stopped monitoring
    hash4 = test_account.send_kin(address, 4, fee=100)
    sleep(10)
    assert not monitor.thread.is_alive()
    assert hash4 not in txs_found


@pytest.mark.skip(reason='Known broken feature on the blockchain')
def test_multi_monitor(test_client, test_account):
    address1 = 'GBMU6NALXWCGEVAU2KKG4KIR3WVRSRRKDQB54VED4MKZZPV653ZVUCNB'
    seed1 = 'SCIVPFA3NFG5Q7W7U3EOP2P33GOETCDMYYIM72BNBD4HKY6WF5J3IE5G'
    test_client.friendbot(address1)

    address2 = 'GB5LRQXPZKCXGTHR2MGD4VNCMV53GJ5WK4NAQOBKRLMGOP3UQJEJMVH2'
    seed2 = 'SAVWARZ7WGUPZJEBIUSQ2ZS4I2PPZILMHWXE7W5OSM2T5BSMCZIBP3G2'
    test_client.friendbot(address2)

    txs_found1 = []
    txs_found2 = []

    def account_tx_callback(addr, tx_data, monitor):
        if addr == address1:
            txs_found1.append(tx_data.id)
        elif addr == address2:
            txs_found2.append(tx_data.id)

    # start monitoring
    monitor = test_client.monitor_accounts_payments([test_account.get_public_address(), address1],
                                                    account_tx_callback)
    assert monitor.thread.is_alive()

    # pay from sdk to the account
    hash1 = test_account.send_kin(address1, 1, fee=100)
    sleep(5)
    assert hash1 in txs_found1

    hash2 = test_account.send_kin(address2, 2, fee=100)
    sleep(5)
    # The second address is not being watched
    assert hash2 not in txs_found2

    monitor.add_address(address2)
    hash3 = test_account.send_kin(address2, 3, fee=100)
    sleep(5)
    assert hash3 in txs_found2

    # stop monitoring
    monitor.stop()
    hash4 = test_account.send_kin(address2, 4, fee=100)
    sleep(10)
    assert not monitor.thread.is_alive()
    assert hash4 not in txs_found2
