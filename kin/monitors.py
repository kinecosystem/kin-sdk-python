"""Contains classes for monitoring the blockchain"""
from threading import Thread, Event

from .blockchain.utils import is_valid_address
from .transactions import OperationTypes, SimplifiedTransaction ,RawTransaction
from .errors import AccountNotFoundError, CantSimplifyError, StoppedMonitorError, StellarAddressInvalidError

import logging

logger = logging.getLogger(__name__)


class SingleMonitor:
    """Single Monitor to monitor Kin payment on a single account"""

    def __init__(self, kin_client, address, callback_fn):
        """
        Monitors a single account for kin payments
        :param kin_client: a kin client directed to the correct network
        :param address: address to watch
        :param callback_fn: function to callback when the payment is found
        """
        self.kin_client = kin_client
        self.callback_fn = callback_fn

        if not address:
            raise ValueError('no address to monitor')

        if not is_valid_address(address):
            raise StellarAddressInvalidError('invalid address: {}'.format(address))

        if not self.kin_client.does_account_exists(address):
            raise AccountNotFoundError(address)

        self.address = address

        # Currently, due to nonstandard SSE implementation in Horizon,
        # using cursor=now will block until the first tx happens.
        # Instead, we determine the cursor ourselves.
        # Fix will be for horizon to send any message just to start a connection.
        # This will cause a tx
        params = {}
        reply = self.kin_client.horizon.account_transactions(address, params={'order': 'desc', 'limit': 2})
        if len(reply['_embedded']['records']) == 2:
            cursor = reply['_embedded']['records'][1]['paging_token']
            params = {'cursor': cursor}

        # make synchronous SSE request (will raise errors in the current thread)
        self.sse_client = self.kin_client.horizon.account_transactions(address, sse=True, params=params)

        self.stop_event = Event()
        # start monitoring thread
        self.thread = Thread(target=self.event_processor, args=(self.stop_event,))
        self.thread.daemon = True
        self.thread.start()

    def event_processor(self, stop_event):
        """
        Method to filter through SSE events and find kin payments for an account
        :param stop_event: an event that can be used to stop this method
        """
        import json
        try:
            for event in self.sse_client:
                if stop_event.is_set():
                    return
                if event.event != 'message':
                    continue
                try:
                    tx = json.loads(event.data)

                    try:
                        tx_data = SimplifiedTransaction(RawTransaction(tx))
                    except CantSimplifyError:
                        continue

                    if tx_data.operation.type != OperationTypes.PAYMENT:
                        continue

                    self.callback_fn(self.address, tx_data, self)

                except Exception as ex:
                    logger.exception(ex)
                    continue
        except TypeError:
            # If we got a type error, that means retry was none, so we should end the thread
            return

    def stop(self):
        """
        Stop monitoring the account.

        The thread will terminate in up to X seconds, where X is the timeout set by the blockchain.
        """

        # Set the stop event, this will terminate the thread once we get the next event from the blockchain.
        self.stop_event.set()

        # Change the retry value,
        # this will cause an exception when trying to reconnect after timeout by the blockchain,
        # which will terminate the thread.
        self.sse_client.retry = None


class MultiMonitor:
    """Multi Monitor to monitor Kin payment on a multiple accounts"""

    def __init__(self, kin_client, addresses, callback_fn):
        """
        Monitors multiple accounts for kin payments
        :param kin_client: a kin client directed to the correct network
        :param addresses: addresses to watch
        :param callback_fn: function to callback when the payment is found
        """
        self.kin_client = kin_client
        self.callback_fn = callback_fn

        if not addresses:
            raise ValueError('no address to monitor')

        for address in addresses:
            if not is_valid_address(address):
                raise StellarAddressInvalidError('invalid address: {}'.format(address))
            if not self.kin_client.does_account_exists(address):
                raise AccountNotFoundError(address)

        self.addresses = addresses

        # Currently, due to nonstandard SSE implementation in Horizon,
        # using cursor=now will block until the first tx happens.
        # Instead, we determine the cursor ourselves.
        # Fix will be for horizon to send any message just to start a connection
        params = {}
        reply = self.kin_client.horizon.transactions(params={'order': 'desc', 'limit': 1})
        if len(reply['_embedded']['records']) == 1:
            cursor = reply['_embedded']['records'][0]['paging_token']
            params = {'cursor': cursor}

        # make synchronous SSE request (will raise errors in the current thread)
        self.sse_client = self.kin_client.horizon.transactions(sse=True, params=params)

        self.stop_event = Event()
        # start monitoring thread
        self.thread = Thread(target=self.event_processor, args=(self.stop_event,))
        self.thread.daemon = True
        self.thread.start()

    def event_processor(self, stop_event):
        """
        Method to filter through SSE events and find kin payments for an account
        :param stop_event: an event that can be used to stop this method
        """
        import json
        try:
            for event in self.sse_client:
                if stop_event.is_set():
                    return
                if event.event != 'message':
                    continue
                try:
                    tx = json.loads(event.data)

                    try:
                        tx_data = SimplifiedTransaction(RawTransaction(tx))
                    except CantSimplifyError:
                        continue

                    if tx_data.operation.type != OperationTypes.PAYMENT:
                        continue

                    if tx_data.source in self.addresses:
                        self.callback_fn(tx_data.source, tx_data, self)
                    if tx_data.operation.destination in self.addresses:
                        self.callback_fn(tx_data.operation.destination, tx_data, self)

                except Exception as ex:
                    logger.exception(ex)
                    continue
        except TypeError:
            # If we got a type error, that means retry was none, so we should end the thread
            return

    def stop(self):
        """
        Stop monitoring the account.

        The thread will terminate in up to X seconds, where X is the timeout set by the blockchain.
        """

        # Set the stop event, this will terminate the thread once we get the next event from the blockchain.
        self.stop_event.set()

        # Change the retry value,
        # this will cause an exception when trying to reconnect after timeout by the blockchain,
        # which will terminate the thread.
        self.sse_client.retry = None

    def add_address(self, address):
        """
        Add address to the watched addresses list
        :param address: address to add
        """
        if address in self.addresses:
            return

        if self.stop_event.is_set():
            raise StoppedMonitorError()

        if not is_valid_address(address):
            raise StellarAddressInvalidError('invalid address: {}'.format(address))

        if not self.kin_client.does_account_exists(address):
            raise AccountNotFoundError(address)

        self.addresses.append(address)

    def remove_address(self, address):
        """
        Remove an address for the list of addresses to watch
        :param address: the address to remove
        """
        if self.stop_event.is_set():
            raise StoppedMonitorError()

        self.addresses.remove(address)
