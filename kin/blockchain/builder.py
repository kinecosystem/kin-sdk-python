"""Contains the builder class to build transactions"""

from kin_base.builder import Builder as BaseBuilder
from kin_base.keypair import Keypair
from kin_base.memo import NoneMemo


class Builder(BaseBuilder):
    """
    This class overrides :class:`kin_base.builder` to provide additional functionality.
    # TODO: maybe merge this with kin-base builder
    """

    # TODO: make seed optional (need to change kin_base)
    def __init__(self, network_name, horizon, fee, secret):
        """
        Create a new transaction builder
        :param str network_name: The name of the network
        :param Kin.Horizon horizon: The horizon instance to use
        :param int fee: Fee for the transaction
        :param str secret: The seed to be used
        """

        # call base class constructor to init base class variables
        # sequence is one since it get overridden later
        super(Builder, self).__init__(secret=secret, sequence=1, fee=fee)

        # custom overrides

        self.network = network_name
        self.horizon = horizon

    def clear(self):
        """"Clears the builder so it can be reused."""
        self.ops = []
        self.time_bounds = None
        self.memo = NoneMemo()
        self.tx = None
        self.te = None

    def update_sequence(self):
        """
        Update the builder with the *current* sequence of the account
        # TODO: kin-base builder increments this value by 1 when building a tx.
        #       Remove this functionality from py-stellar-base and change this method set the current sequence+1
        """

        # TODO: kin-base checks for 'not sequence' to find if there is no sequence, therefore
        # Sequence of 0 fails, write it as a str for now and fix in kin-base later
        self.sequence = str(self.get_sequence())

    def next(self):
        """
        Alternative implementation that does not create a new builder but clears the current one and increments
        the account sequence number.
        """
        self.clear()
        self.sequence = str(int(self.sequence) + 1)

    def set_channel(self, channel_seed):
        """
        Set a channel to be used for this transaction
        :param channel_seed: Seed to use as the channel
        """
        self.keypair = Keypair.from_seed(channel_seed)
        self.address = self.keypair.address().decode()
        self.update_sequence()
