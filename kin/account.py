"""Contains the Account class."""

from .blockchain.keypair import Keypair
from .blockchain.horizon import Horizon
from .blockchain.channel_manager import ChannelManager
from .errors import AccountExistsError, LowBalanceError
from .config import MIN_ACCOUNT_BALANCE, SDK_USER_AGENT
from .blockchain.utils import is_valid_secret_key


class KinAccount:
    """Account class to perform authenticated actions on the blockchain"""
    def __init__(self, seed, client, channels, channel_secret_keys, create_channels):
        # Set the internal sdk
        self._client = client

        if not is_valid_secret_key(seed):
            raise ValueError('invalid secret key: {}'.format(seed))
        self.keypair = Keypair(seed)
        # check that sdk wallet account exists and is activated
        self._client._get_account_asset_balance(self.keypair.public_address, self.kin_asset)

        if channels is not None and channel_secret_keys is not None:
            raise ValueError("Account cannot be initialized with both 'channels'"
                             " and 'channel_secret_keys' parameters")

        if channel_secret_keys is not None:
            # Use given channels
            for channel_key in channel_secret_keys:
                if not is_valid_secret_key(channel_key):
                    raise ValueError('invalid channel key: {}'.format(channel_key))
                    # check that channel accounts exist (they do not have to be activated.
                channel_address = Keypair.address_from_seed(channel_key)
                self._client.get_account_data(channel_address)
            self.channel_secret_keys = channel_secret_keys

        elif channels is not None:
            # Generate the channels for the user
            self.channel_secret_keys = [Keypair.generate_hd_seed(seed, channel) for channel in range(channels)]
        else:
            self.channel_secret_keys = [seed]

        if create_channels:
            # Create the channels using the base account
            if not channel_secret_keys:
                raise ValueError('There are no channels to create')
            base_account = KinAccount(seed,self._client, None, None, False)

            # Verify that there is enough XLM to create the channels
            # Balance should be atleast (Number of channels + yourself) * (Minimum account balance + fees)
            if (len(channel_secret_keys) + 1) * (MIN_ACCOUNT_BALANCE + 0.00001) > \
                    base_account.get_balances()['Native']:
                raise LowBalanceError('The base account does not have enough XLM to create the channels')

            # Create the channels, pass if the channel already exists
            for channel in channel_secret_keys:
                try:
                    base_account.create_account(channel)
                except AccountExistsError:
                    pass

        # set connection pool size for channels + monitoring connection + extra
        pool_size = max(1, len(channel_secret_keys)) + 2
        self.horizon = Horizon(self._client.environment.horizon_uri, pool_size=pool_size , user_agent=SDK_USER_AGENT)
        self.channel_manager = ChannelManager(seed, channel_secret_keys, self._client.environment.name, self.horizon)

    def create_account(self,address):
        pass #TODO