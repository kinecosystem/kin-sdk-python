"""Contains the Environment class to configure horizon"""

from hashlib import sha256

from stellar_base.network import NETWORKS
from stellar_base.asset import Asset

from .utils import is_valid_address


class Environment:
    """Environments holds the parameters that will be used to connect to horizon"""
    def __init__(self, name, horizon_endpoint_uri, network_passphrase, kin_issuer, friendbot_url=None):
        """

        :param str name: Name of the environment.
        :param str horizon_uri: a Horizon endpoint.
        :param str network_passphrase: The passphrase/network_id of the environment.
        :param str kin_issuer: The issuer of the KIN asset.
        :param str friendbot_url: a url to a friendbot service
        :return: An instance of the Environment class.
        :rtype: :class: `kin.Environment`

        :raises: ValueError: is the kin_issuer is invalid
        """
        # Add the network to the stellar_base network list.
        NETWORKS[name.upper()] = network_passphrase
        self.name = name.upper()
        self.horizon_uri = horizon_endpoint_uri

        if not is_valid_address(kin_issuer):
            raise ValueError('invalid issuer {}'.format(kin_issuer))
        self.kin_asset = Asset('KIN', kin_issuer)
        self.friendbot_url = friendbot_url

        # Calculate the hash of the passphrase, can be used to calculate tx hash.
        self.passphrase_hash = sha256(network_passphrase.encode()).digest()
