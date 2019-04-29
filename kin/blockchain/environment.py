"""Contains the Environment class to configure horizon"""

from hashlib import sha256

from kin_base.network import NETWORKS

from typing import Optional


class Environment:
    def __init__(self, name: str, horizon_endpoint_uri: str, network_passphrase: str,
                 friendbot_url: Optional[str] = None):
        """
        Environments holds the parameters that will be used to connect to horizon

        :param name: Name of the environment.
        :param horizon_endpoint_uri: a Horizon endpoint.
        :param network_passphrase: The passphrase/network_id of the environment.
        :param friendbot_url: a url to a friendbot service
        :return: An instance of the Environment class.
        """
        # Add the network to the kin_base network list.
        NETWORKS[name.upper()] = network_passphrase
        self.name = name.upper()
        self.horizon_uri = horizon_endpoint_uri
        self.friendbot_url = friendbot_url
        self.passphrase = network_passphrase

        # Calculate the hash of the passphrase, can be used to calculate tx hash.
        self.passphrase_hash = sha256(network_passphrase.encode()).digest()

    def __str__(self):
        string_representation = '<Kin Environment>: Name: {}, ' \
                                'Horizon: {}, ' \
                                'Passphrase: {}'.format(self.name, self.horizon_uri, self.passphrase)
        return string_representation
