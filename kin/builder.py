# -*- coding: utf-8 -*

# Copyright (C) 2018 Kin Foundation

import stellar_base.builder
from stellar_base.memo import NoneMemo


class Builder(stellar_base.builder.Builder):
    """
    This class overrides :class:`~stellar_base.builder` to provide additional functionality.
    """
    def __init__(self, secret=None, address=None, horizon=None, network=None, sequence=None):
        super(Builder, self).__init__(secret, address, horizon, network, sequence)
        # fix network property to receive custom values
        if network and network.upper() != 'PUBLIC' and network.upper() != 'TESTNET':
            self.network = network.upper()

    def clear(self):
        """"Clears the builder so it can be reused."""
        self.ops = []
        self.time_bounds = []
        self.memo = NoneMemo()
        self.fee = None
        self.tx = None
        self.te = None

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
        self.sequence = self.get_sequence()
        super(Builder, self).sign(secret)
