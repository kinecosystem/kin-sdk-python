"""Contains the Environment class to configure horizon"""

from hashlib import sha256

from kin_base.network import NETWORKS
from kin_base.asset import Asset
from kin_base.exceptions import StellarAddressInvalidError

from .utils import is_valid_address


class Environment:
    """Environments holds the parameters that will be used to connect to horizon"""
    def __init__(self, name, horizon_endpoint_uri, network_passphrase, friendbot_url=None):
        """

        :param str name: Name of the environment.
        :param str horizon_uri: a Horizon endpoint.
        :param str network_passphrase: The passphrase/network_id of the environment.
        :param str friendbot_url: a url to a friendbot service
        :return: An instance of the Environment class.
        :rtype: :class: `kin.Environment`

        :raises: ValueError: is the kin_issuer is invalid
        """
        # Add the network to the kin_base network list.
        NETWORKS[name.upper()] = network_passphrase
        self.name = name.upper()
        self.horizon_uri = horizon_endpoint_uri
        self.friendbot_url = friendbot_url

        # Calculate the hash of the passphrase, can be used to calculate tx hash.
        self.passphrase_hash = sha256(network_passphrase.encode()).digest()
