"""Contain the Keypair class and related methods"""

from hashlib import sha256

from kin_base.keypair import Keypair as BaseKeypair
from kin_base.exceptions import StellarSecretInvalidError
from kin_base.stellarxdr.StellarXDR_type import DecoratedSignature

from .utils import is_valid_secret_key


class Keypair:
    """A simpler version of kin_base.Keypair that holds the public address and secret seed."""

    def __init__(self, seed=None):
        """
        # Create an instance of Keypair.
        :param seed: (Optional) The secret seed of an account
        """
        self.secret_seed = seed or self.generate_seed()
        if not is_valid_secret_key(self.secret_seed):
            raise StellarSecretInvalidError('invalid seed {}'.format(self.secret_seed))
        base_keypair = BaseKeypair.from_seed(self.secret_seed)
        self.public_address = base_keypair.address().decode()

        # Hint and signing key are needed to sign the tx
        self._hint = base_keypair.signature_hint()
        self._signing_key = base_keypair.signing_key

    def sign(self, data):
        """
        Sign any data using the keypair private key
        :param bytes data: any data to sign
        :return: a decorated signature
        :rtype :class: DecoratedSignature
        """
        signature = self._signing_key.sign(data)
        return DecoratedSignature(self._hint, signature)

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
        :param salt: A unique string that will be used to generate the seed
        :return: a new seed.
        """
        # Create a new raw seed from this hash
        raw_seed = sha256((base_seed + salt).encode()).digest()
        return BaseKeypair.from_raw_seed(raw_seed).seed().decode()
