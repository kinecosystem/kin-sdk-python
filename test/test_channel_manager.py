import pytest
from kin import KinErrors

from kin.blockchain.channel_manager import ChannelManager, ChannelStatuses, ChannelPool

channels = ['SAL3KMFKZJB6UEHHBEFTSH6RZITRJM4CITECSFBSKIYBT6YKQFTKIEY7',
            'SAY2PD4ZOIFYNXJTY77WUFQMHYXUVHXC2DM5F6VAHAWTBPORA2GQDNTA',
            'SBTYCBDS2CMZXPGWEVKWBJ5SIQYA56O5OAXB7VPD6OP7NYWF3O2WFQQS',
            'SAKYE7ADKB2ASQ5C63RTKINTXWJQH4ERR57KDTTLOKRD262C2KMDAUGS',
            'SCPI7MYQIY6SCBQLBUZXD4KZBFCIAQWDS5ELNFC3ZIEZWJAN5HCEAAVP']


def test_create_channel_manager():
    manager = ChannelManager(channels)
    assert manager
    assert manager.channel_pool


def test_create_channel_pool():
    pool = ChannelPool(channels)
    assert len(channels) == len(pool.queue)
    for channel in channels:
        assert pool.queue[channel] == ChannelStatuses.FREE


def test_pool_get_and_put():
    pool = ChannelPool(channels)
    channel = pool.get()
    assert pool.queue[channel] == ChannelStatuses.TAKEN
    pool.put(channel)
    assert pool.queue[channel] == ChannelStatuses.FREE


def test_q_size():
    pool = ChannelPool(channels)
    assert pool.qsize() == 5


def test_get_available_channels():
    pool = ChannelPool(channels)
    free_channels = pool.get_free_channels()
    assert len(free_channels) == 5
    for channel in free_channels:
        assert pool.queue[channel] == ChannelStatuses.FREE


def test_get_channel():
    manager = ChannelManager(channels)
    with manager.get_channel() as channel:
        assert manager.channel_pool.queue[channel] == ChannelStatuses.TAKEN
    assert manager.channel_pool.queue[channel] == ChannelStatuses.FREE