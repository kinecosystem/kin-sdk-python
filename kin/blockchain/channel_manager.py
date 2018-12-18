"""Contains classes and methods related to channels"""

import sys
import random
from contextlib import contextmanager
from enum import Enum

from .errors import ChannelsBusyError, ChannelsFullError

if sys.version[0] == '2':
    import Queue as queue
else:
    import queue

CHANNEL_GET_TIMEOUT = 11  # how much time to wait until a channel is available, in seconds
CHANNEL_PUT_TIMEOUT = 0.5  # how much time to wait for a channel to return to the queue


class ChannelManager:
    """Provide useful methods to interact with the underlying ChannelPool"""

    def __init__(self, channel_seeds):
        """
        Crete a channel manager instance
        :param list[str] channel_seeds: The seeds of the channels to use
        """
        self.channel_pool = ChannelPool(channel_seeds)

    @contextmanager
    def get_channel(self, timeout=CHANNEL_GET_TIMEOUT):
        """
        Get an available channel
        :param float timeout: (Optional) How long to wait before raising an exception
        :return a free channel seed
        :rtype str

        :raises KinErrors.ChannelBusyError
        """
        try:
            channel = self.channel_pool.get(timeout=timeout)
        except queue.Empty:
            raise ChannelsBusyError()

        try:
            yield channel
        finally:
            if self.channel_pool.queue[channel] != ChannelStatuses.UNDERFUNDED:
                self.put_channel(channel)

    def put_channel(self, channel, timeout=CHANNEL_PUT_TIMEOUT):
        """
        Set a channel status back to FREE
        :param str channel: the channel to set back to FREE
        :param float timeout: (Optional) How long to wait before raising an exception

        :raises KinErrors.ChannelsFullError
        """
        try:
            self.channel_pool.put(channel, timeout=timeout)
        except queue.Full:
            raise ChannelsFullError()

    def get_status(self, verbose=False):
        """
        Return the current status of the channel manager
        :param bool verbose: Include all channel seeds and their statuses in the response
        :return: dict
        """
        free_channels = len(self.channel_pool.get_free_channels())
        status = {
            'total_channels': len(self.channel_pool.queue),
            'free_channels': free_channels,
            'non_free_channels': len(self.channel_pool.queue) - free_channels
        }
        if verbose:
            status['channels'] = self.channel_pool.queue

        return status


class ChannelStatuses(str, Enum):
    """Contains possible statuses for channels"""
    # subclass str to be able to serialize to json
    FREE = 'free'
    TAKEN = 'taken'
    UNDERFUNDED = 'underfunded'


# TODO: remove object when we kill python2
class ChannelPool(queue.Queue, object):
    """
    A thread-safe queue that sets a member's status instead of pulling it in/out of the queue.
    This queue gets members randomly when 'get' is used, as opposed to always get the last member.
    """
    def __init__(self, channels_seeds):
        """
        Create an instance of ChannelPool
        :param list[str] channels_seeds: The seeds to be put in the queue
        """
        # Init base queue
        super(ChannelPool, self).__init__(len(channels_seeds))
        # Change queue from a 'deque' object to a dict full of free channels
        self.queue = {channel: ChannelStatuses.FREE for channel in channels_seeds}

    def _get(self):
        """
        Randomly get an available free channel from the dict
        :return: a channel seed
        :rtype str
        """
        # Get a list of all free channels
        free_channels = self.get_free_channels()
        # Select a random free channel
        selected_channel = random.choice(free_channels)
        # Change channel state to taken
        self.queue[selected_channel] = ChannelStatuses.TAKEN
        return selected_channel

    def _put(self, channel):
        """
        Change a channel status back to FREE
        :param str channel: the channel seed
        """
        # Change channel state to free
        self.queue[channel] = ChannelStatuses.FREE

    def _qsize(self):
        """
        Used to determine if the queue is empty
        :return: amount of free channels in the queue
        :rtype int
        """
        # Base queue checks if the queue is not empty by checking the length of the queue (_qsize() != 0)
        # We need to check it by checking how many channels are free
        return len(self.get_free_channels())

    def get_free_channels(self):
        """
        Get a list of channels with "FREE" status
        :rtype list[str]
        """
        return [channel for channel, status in self.queue.items() if status == ChannelStatuses.FREE]

