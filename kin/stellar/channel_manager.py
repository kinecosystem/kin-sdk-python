# -*- coding: utf-8 -*

# Copyright (C) 2018 Kin Foundation

import sys
from time import sleep

from stellar_base.keypair import Keypair

from .builder import Builder
from .errors import ChannelsBusyError, HorizonError, HorizonErrorType, TransactionResultCode

import logging
logger = logging.getLogger(__name__)

if sys.version[0] == '2':
    import Queue as queue
else:
    # noinspection PyUnresolvedReferences
    import queue as queue

CHANNEL_QUEUE_TIMEOUT = 11  # how much time to wait until a channel is available, in seconds


class ChannelManager(object):
    """ The class :class:`kin.ChannelManager` wraps channel-related specifics of transaction sending."""
    def __init__(self, secret_key, channel_keys, network, horizon):
        self.base_key = secret_key
        self.base_address = Keypair.from_seed(secret_key).address().decode()
        self.num_channels = len(channel_keys)
        self.channel_builders = queue.Queue(len(channel_keys))
        self.horizon = horizon
        for channel_key in channel_keys:
            # create a channel transaction builder.
            builder = Builder(secret=channel_key, network=network, horizon=horizon)
            self.channel_builders.put(builder)

    def send_transaction(self, add_ops_fn, memo_text=None):
        """Send a transaction using an available channel account.

        :param add_ops_fn: a function to call, that will add operations to the transaction. The function should be
            `partial`, because a `source` parameter will be added.
        :type add_ops_fn: callable[builder]

        :param str memo_text: (optional) a text to add as transaction memo.

        :return: transaction object
        :rtype: dict
        """
        # send and retry bad sequence errors
        retry_count = self.horizon.num_retries
        while True:
            # get an available channel builder first (blocking with timeout)
            try:
                builder = self.channel_builders.get(True, CHANNEL_QUEUE_TIMEOUT)
            except queue.Empty:
                raise ChannelsBusyError

            retrying = False
            try:
                # operation source is always the base account
                source = self.base_address if builder.address != self.base_address else None

                # add operation (using external partial) and sign
                add_ops_fn(builder)(source=source)
                if memo_text:
                    builder.add_text_memo(memo_text[:28])  # max memo length is 28

                builder.sign()  # always sign with a channel key
                if source:
                    builder.sign(secret=self.base_key)  # sign with the base key if needed
                return builder.submit()
            except HorizonError as e:
                logging.warning('send transaction error with channel {}: {}'.format(builder.address, str(e)))
                # retry bad sequence error
                if e.type == HorizonErrorType.TRANSACTION_FAILED \
                        and e.extras.result_codes.transaction == TransactionResultCode.BAD_SEQUENCE \
                        and retry_count > 0:
                            retrying = True
                            retry_count -= 1
                            logging.warning('send transaction retry attempt {}'.format(retry_count))
                            continue
                raise
            finally:
                # always clean the builder and return it to the queue
                builder.clear()
                self.channel_builders.put(builder)
                if retrying:
                    sleep(builder.horizon.backoff_factor)
