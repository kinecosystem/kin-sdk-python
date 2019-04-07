"""Contains helper methods for the kin sdk"""

from hashlib import sha256

from kin_base import Builder

from .client import KinClient
from .blockchain.keypair import Keypair
from .errors import AccountNotFoundError
from .blockchain.environment import Environment

from typing import List


async def create_channels(master_seed: str, environment: Environment, amount: int,
                          starting_balance: float, salt: str) -> List[str]:
    """
    Create HD seeds based on a master seed and salt

    :param master_seed: The master seed that creates the seeds
    :param environment: The blockchain environment to create the seeds on
    :param amount: Number of seeds to create (Up to 100)
    :param starting_balance: Starting balance to create channels with
    :param salt: A string to be used to create the HD seeds
    :return: The list of seeds generated
    """

    async with KinClient(environment) as client:
        base_key = Keypair(master_seed)
        if not await client.does_account_exists(base_key.public_address):
            raise AccountNotFoundError(base_key.public_address)

        fee = await client.get_minimum_fee()

        channels = get_hd_channels(master_seed, salt, amount)

        # Create a builder for the transaction
        builder = Builder(client.horizon, environment.name, fee, master_seed)

        # Find out if this salt+seed combination was ever used to create channels.
        # If so, the user might only be interested in adding channels,
        # so we need to find what seed to start from

        # First check if the last channel exists, if it does, we don't need to create any channel.
        if await client.does_account_exists(Keypair.address_from_seed(channels[-1])):
            return channels

        for index, seed in enumerate(channels):
            if await client.does_account_exists(Keypair.address_from_seed(seed)):
                continue

            # Start creating from the current seed forward
            for channel_seed in channels[index:]:
                builder.append_create_account_op(Keypair.address_from_seed(channel_seed), str(starting_balance))

            await builder.update_sequence()
            builder.sign()
            await builder.submit()
            break

    return channels


def get_hd_channels(master_seed: str, salt: str, amount: int) -> List[str]:
    """
    Get a list of channels generated based on a seed and salt

    :param master_seed: the base seed that created the channels
    :param salt: A string to be used to generate the seeds
    :param amount: Number of seeds to generate (Up to 100)
    :return: The list of seeds generated
    :rtype list[str]
    """

    if amount > 100:
        """
        The sdk's channels are not meant to be shared across multiple instances of the script,
        and a single instance will never even use 100 channels at once.
        This is a limit to stop developers from needlessly creating a huge amount of channels
        """
        raise ValueError('Only up to 100 channels can be created with a specific seed + salt combination')
    hashed_salt = sha256(salt.encode()).hexdigest()

    channels = []
    for index in range(amount):
        # The salt used to generate the
        channel = Keypair.generate_hd_seed(master_seed, hashed_salt + str(index))
        channels.append(channel)

    return channels




