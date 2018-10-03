"""Contain the Keypair class and related methods"""

from hashlib import sha256

from stellar_base.keypair import Keypair as BaseKeypair

from .utils import is_valid_secret_key


class Keypair:
    """Keypair holds the public address and secret seed."""

    def __init__(self, seed=None):
        """
        # Create an instance of Keypair.
        :param seed: (Optional) The secret seed of an account
        """
        self.secret_seed = seed or self.generate_seed()
        if not is_valid_secret_key(self.secret_seed):
            raise ValueError('invalid seed {}'.format(self.secret_seed))
        self.public_address = Keypair.address_from_seed(self.secret_seed)

    @staticmethod
    def address_from_seed(seed):
        """
        Get a public address from a secret seed.
        :param seed: The secret seed of an account.
        :return: A public address.
        """
        return BaseKeypair.from_seed(seed).address().decode()

    @staticmethod
    def generate_seed():
        """
        Generate a random secret seed.
        :return: A secret seed.
        """
        return BaseKeypair.random().seed().decode()

    @staticmethod
    def generate_hd_seed(base_seed, salt):
        """
        Generate a highly deterministic seed from a base seed + salt
        :param base_seed: The base seed to generate a seed from
        :param salt: A uniqe string that will be used to generate the seed
        :return: a new seed.
        """
        # Create a new raw seed from the first 32 bytes of this hash
        raw_seed = sha256((base_seed + salt).encode()).digest()[:32]
        return BaseKeypair.from_raw_seed(raw_seed).seed().decode()
