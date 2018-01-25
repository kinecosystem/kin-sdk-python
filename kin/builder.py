
import stellar_base.builder
from stellar_base.memo import NoneMemo


class Builder(stellar_base.builder.Builder):
    def __init__(self, secret=None, address=None, horizon=None, network=None, sequence=None):
        super(Builder, self).__init__(secret, address, horizon, network, sequence)
        # fix network property to receive custom values
        if network and network.upper() != 'PUBLIC' and network.upper() != 'TESTNET':
            self.network = network.upper()

    def clear(self):
        self.ops = []
        self.time_bounds = []
        self.memo = NoneMemo()
        self.fee = None
        self.tx = None
        self.te = None

    def next(self):
        self.clear()
        self.sequence = str(int(self.sequence) + 1)

    def sign(self, secret=None):
        self.sequence = self.get_sequence()
        super(Builder, self).sign(secret)
