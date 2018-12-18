"""Contains helper methods for the kin sdk"""

from hashlib import sha256

from .client import KinClient
from .blockchain.builder import Builder
from .blockchain.keypair import Keypair
from .errors import AccountNotFoundError


def create_channels(master_seed, environment, amount, starting_balance, salt):
    """
    Create HD seeds based on a master seed and salt
    :param str master_seed: The master seed that creates the seeds
    :param Kin.Environment environment: The blockchain environment to create the seeds on
    :param int amount: Number of seeds to create (Up to 100)
    :param float starting_balance: Starting balance to create channels with
    :param str salt: A string to be used to create the HD seeds
    :return: The list of seeds generated
    :rtype list[str]
    """

    client = KinClient(environment)
    base_key = Keypair(master_seed)
    if not client.does_account_exists(base_key.public_address):
        raise AccountNotFoundError(base_key.public_address)

    fee = client.get_minimum_fee()

    channels = get_hd_channels(master_seed, salt, amount)

    # Create a builder for the transaction
    builder = Builder(environment.name, client.horizon, fee, master_seed)

    # Find out if this salt+seed combination was ever used to create channels.
    # If so, the user might only be interested in adding channels,
    # so we need to find what seed to start from

    # First check if the last channel exists, if it does, we don't need to create any channel.
    if client.does_account_exists(Keypair.address_from_seed(channels[-1])):
        return channels

    for index, seed in enumerate(channels):
        if client.does_account_exists(Keypair.address_from_seed(seed)):
            continue

        # Start creating from the current seed forward
        for channel_seed in channels[index:]:
            builder.append_create_account_op(Keypair.address_from_seed(channel_seed), str(starting_balance))

        builder.sign()
        builder.submit()
        break

    return channels


def get_hd_channels(master_seed, salt, amount):
    """
    Get a list of channels generated based on a seed and salt
    :param str master_seed: the base seed that created the channels
    :param str salt: A string to be used to generate the seeds
    :param int amount: Number of seeds to generate (Up to 100)
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




