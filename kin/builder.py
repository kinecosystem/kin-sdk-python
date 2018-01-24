
import stellar_base.builder
from stellar_base.memo import NoneMemo


class Builder(stellar_base.builder.Builder):

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
