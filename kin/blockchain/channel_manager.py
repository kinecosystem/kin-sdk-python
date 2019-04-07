"""Contains classes and methods related to channels"""

import sys
import random
from asyncio.queues import Queue as queue
from enum import Enum

from typing import List, Optional

# Python 3.6 didnt support asynccontextmanager, so the kin-sdk installs a backport for it
if sys.version_info.minor == 6:
    from async_generator import asynccontextmanager
else:
    from contextlib import asynccontextmanager


class ChannelManager:
    """Provide useful methods to interact with the underlying ChannelPool"""

    def __init__(self, channel_seeds: List[str]):
        """
        Crete a channel manager instance

        :param channel_seeds: The seeds of the channels to use
        """
        self.channel_pool = ChannelPool(channel_seeds)

    @asynccontextmanager
    async def get_channel(self) -> str:
        """
        Get an available channel

        :return a free channel seed

        """
        channel = await self.channel_pool.get()

        try:
            yield channel
        finally:
            if self.channel_pool._queue[channel] != ChannelStatuses.UNDERFUNDED:
                await self.put_channel(channel)

    async def put_channel(self, channel) -> None:
        """
        Set a channel status back to FREE

        :param str channel: the channel to set back to FREE
        """
        await self.channel_pool.put(channel)

    def get_status(self, verbose: Optional[bool] = False) -> dict:
        """
        Return the current status of the channel manager

        :param verbose: Include all channel seeds and their statuses in the response
        :return: The status of the channel manager
        """
        free_channels = len(self.channel_pool.get_free_channels())
        status = {
            'total_channels': len(self.channel_pool._queue),
            'free_channels': free_channels,
            'non_free_channels': len(self.channel_pool._queue) - free_channels
        }
        if verbose:
            status['channels'] = self.channel_pool._queue

        return status


class ChannelStatuses(str, Enum):
    """Contains possible statuses for channels"""

    # subclass str to be able to serialize to json
    FREE = 'free'
    TAKEN = 'taken'
    UNDERFUNDED = 'underfunded'


class ChannelPool(queue):
    """
    An async queue that sets a member's status instead of pulling it in/out of the queue.
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
        self._queue = {channel: ChannelStatuses.FREE for channel in channels_seeds}

    def _get(self) -> str:
        """
        Randomly get an available free channel from the dict

        :return: a channel seed
        """
        # Get a list of all free channels
        free_channels = self.get_free_channels()
        # Select a random free channel
        selected_channel = random.choice(free_channels)
        # Change channel state to taken
        self._queue[selected_channel] = ChannelStatuses.TAKEN
        return selected_channel

    def _put(self, channel: str) -> None:
        """
        Change a channel status back to FREE

        :param str channel: the channel seed
        """
        # Change channel state to free
        self._queue[channel] = ChannelStatuses.FREE

    def qsize(self) -> int:
        """
        Counts free channels in the queue

        :return: amount of free channels in the queue
        """
        return len(self.get_free_channels())

    def empty(self) -> bool:
        """Used to check if the queue is empty"""
        return len(self.get_free_channels()) == 0

    def get_free_channels(self) -> List[str]:
        """Get a list of channels with "FREE" status"""
        return [channel for channel, status in self._queue.items() if status == ChannelStatuses.FREE]

