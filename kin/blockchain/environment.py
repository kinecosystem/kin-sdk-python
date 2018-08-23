"""Contains the Environment class to configure horizon"""
from hashlib import sha256
from binascii import hexlify

from stellar_base.network import NETWORKS
from stellar_base.asset import Asset



class Environment:
    # Environments holds the parameters that will be used to connect to horizon
    def __init__(self, name, horizon_endpoint_uri, network_passphrase, kin_issuer):
        """

        :param name: Name of the environment.
        :param horizon_uri: a Horizon endpoint.
        :param network_passphrase: The passphrase/network_id of the environment.
        :param kin_issuer: The issuer of the KIN asset.
        :return: An instance of the Environment class.
        """
        # Add the network to the stellar_base network list.
        NETWORKS[name.upper()] = network_passphrase
        self.name = name
        self.horizon_uri = horizon_endpoint_uri
        self.kin_asset = Asset('KIN',kin_issuer)

        # Calculate the hash of the passphrase, can be used to calculate tx hash.
        self.passphrase_hash = hexlify(sha256(network_passphrase.encode()).digest())
