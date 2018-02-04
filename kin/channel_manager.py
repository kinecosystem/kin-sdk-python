# -*- coding: utf-8 -*

# Copyright (C) 2018 Kin Foundation

import sys

from stellar_base.keypair import Keypair

from .builder import Builder
from .utils import check_horizon_reply

if sys.version[0] == '2':
    import Queue as queue
else:
    import queue as queue


class ChannelManager(object):
    """ The class :class:`~kin.ChannelManager` wraps channel-related specifics of transaction sending."""
    def __init__(self, base_seed, channel_seeds, network, horizon):
        self.base_seed = base_seed
        self.base_address = Keypair.from_seed(base_seed).address().decode()
        self.channel_builders = queue.Queue(len(channel_seeds))
        for channel_seed in channel_seeds:
            # create a channel transaction builder and load channel account sequence number.
            builder = Builder(secret=channel_seed, network=network, horizon=horizon)
            self.channel_builders.put(builder)

    def send_transaction(self, add_ops_fn, memo_text=None):
        """Send a transaction using an available channel account.

        :param add_ops_fn: a function to call, that will add operations to the transaction. The function should be
            `partial`, because a `source` parameter will be added.

        :param str memo_text: an optional text to add as transaction memo.

        :return: transaction hash
        :rtype: str
        """
        # get an available channel builder first (blocking)
        builder = self.channel_builders.get(True)
        try:
            # operation source is always the base account
            source = self.base_address if builder.address != self.base_address else None
            add_ops_fn(builder)(source=source)
            if memo_text:
                builder.add_text_memo(memo_text[:28])  # max memo length is 28
            builder.sign()  # always sign with a channel key
            if source:
                builder.sign(secret=self.base_seed)  # sign with base key too
            reply = builder.submit()
            check_horizon_reply(reply)
            return reply.get('hash')
        finally:
            # clean the builder and return it to the queue
            builder.clear()
            self.channel_builders.put(builder)
