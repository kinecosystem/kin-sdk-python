"""Contains the builder class to build transactions"""

from stellar_base.builder import Builder as BaseBuilder
from stellar_base.keypair import Keypair
from stellar_base.memo import NoneMemo

from .utils import is_valid_address, is_valid_secret_key


class Builder(BaseBuilder):
    """
    This class overrides :class:`stellar_base.builder` to provide additional functionality.
    """

    def __init__(self, network, horizon, secret=None, address=None):
        if secret:
            if not is_valid_secret_key(secret):
                raise ValueError('invalid secret key')
            address = Keypair.from_seed(secret).address().decode()
        elif address:
            if not is_valid_address(address):
                raise ValueError('invalid address')
        else:
            raise Exception('either secret or address must be provided')

        # call baseclass constructor to init base class variables
        super(Builder, self).__init__(secret=secret, address=address, sequence=1)

        # custom overrides

        self.network = network
        self.horizon = horizon

    def clear(self):
        """"Clears the builder so it can be reused."""
        self.ops = []
        self.time_bounds = []
        self.memo = NoneMemo()
        self.fee = 100
        self.tx = None
        self.te = None

    def get_sequence(self):
        """Alternative implementation to expose exceptions"""
        return self.horizon.account(self.address).get('sequence')

    def next(self):
        """
        Alternative implementation that does not create a new builder but clears the current one and increments
        the account sequence number.
        """
        self.clear()
        self.sequence = str(int(self.sequence) + 1)

    def sign(self, secret=None):
        """
        Alternative implementation that does not use the self-managed sequence, but always fetches it from Horizon.
        """
        if not secret:  # only get the new sequence for my own account
            self.sequence = self.get_sequence()
        super(Builder, self).sign(secret)

    def append_create_account_op(self, destination, starting_balance, source=None, kin_asset=None):
        """
        Alternative implementation that allows to create a trustline
        in addition to the create account operation
        Needs to be supported by the blockchain
        """
        super(Builder, self).append_create_account_op(destination, starting_balance, source)
        if kin_asset:
            # Source for the trust op should be the created account
            super(Builder, self).append_trust_op(kin_asset.issuer, kin_asset.code, source=destination)
