# -*- coding: utf-8 -*

# Copyright (C) 2018 Kin Foundation

import requests
from requests.adapters import HTTPAdapter, DEFAULT_POOLSIZE
from urllib3.util import Retry
import sys

try:
    from sseclient import SSEClient
except ImportError:
    SSEClient = None

if sys.version[0] == '2':
    from urllib import urlencode
else:
    from urllib.parse import urlencode

from stellar_base.horizon import HORIZON_LIVE, HORIZON_TEST

from .version import __version__ as sdk_version

import logging
logger = logging.getLogger(__name__)


DEFAULT_REQUEST_TIMEOUT = 11  # two ledger times + extra
DEFAULT_NUM_RETRIES = 3
DEFAULT_BACKOFF_FACTOR = 0.3
USER_AGENT = 'kin-stellar-python/{}'.format(sdk_version)


class Horizon(object):
    """
    This class redefines :class:`~stellar_base.horizon_uri` to provide additional functionality.
    """
    def __init__(self, horizon_uri=None, pool_size=DEFAULT_POOLSIZE, num_retries=DEFAULT_NUM_RETRIES,
                 request_timeout=DEFAULT_REQUEST_TIMEOUT, backoff_factor=DEFAULT_BACKOFF_FACTOR):
        if horizon_uri is None:
            self.horizon_uri = HORIZON_TEST
        else:
            self.horizon_uri = horizon_uri

        self.request_timeout = request_timeout

        # init transport adapter
        adapter = HTTPAdapter(pool_connections=1, pool_maxsize=pool_size)
        adapter.max_retries = Retry(total=num_retries, backoff_factor=backoff_factor, redirect=0)

        # init session
        session = requests.Session()

        # set default headers
        session.headers.update({'User-Agent': USER_AGENT})

        session.mount('http://', adapter)
        session.mount('https://', adapter)
        self._session = session

    def submit(self, te):
        params = {'tx': te}
        url = self.horizon_uri + '/transactions/'
        return self._session.post(url, data=params, timeout=self.request_timeout).json()

    def query(self, rel_url, params=None, sse=False):
        abs_url = self.horizon_uri + rel_url
        return self._query(abs_url, params, sse)

    def accounts(self, params=None, sse=False):
        url = '/accounts/'
        return self.query(url, params, sse)

    def account(self, address):
        url = '/accounts/' + address
        return self.query(url)

    def account_effects(self, address, params=None, sse=False):
        url = '/accounts/' + address + '/effects/'
        return self.query(url, params, sse)

    def account_offers(self, address, params=None):
        url = '/accounts/' + address + '/offers/'
        return self.query(url, params)

    def account_operations(self, address, params=None, sse=False):
        url = '/accounts/' + address + '/operations/'
        return self.query(url, params, sse)

    def account_transactions(self, address, params=None, sse=False):
        url = '/accounts/' + address + '/transactions/'
        return self.query(url, params, sse)

    def account_payments(self, address, params=None, sse=False):
        url = '/accounts/' + address + '/payments/'
        return self.query(url, params, sse)

    def transactions(self, params=None, sse=False):
        url = '/transactions/'
        return self.query(url, params, sse)

    def transaction(self, tx_hash):
        url = '/transactions/' + tx_hash
        return self.query(url)

    def transaction_operations(self, tx_hash, params=None):
        url = '/transactions/' + tx_hash + '/operations/'
        return self.query(url, params)

    def transaction_effects(self, tx_hash, params=None):
        url = '/transactions/' + tx_hash + '/effects/'
        return self.query(url, params)

    def transaction_payments(self, tx_hash, params=None):
        url = '/transactions/' + tx_hash + '/payments/'
        return self.query(url, params)

    def order_book(self, params=None):
        url = '/order_book/'
        return self.query(url, params)

    def order_book_trades(self, params=None):
        url = '/order_book/trades/'
        return self.query(url, params)

    def ledgers(self, params=None, sse=False):
        url = '/ledgers/'
        return self.query(url, params, sse)

    def ledger(self, ledger_id):
        url = '/ledgers/' + ledger_id
        return self.query(url)

    def ledger_effects(self, ledger_id, params=None):
        url = '/ledgers/' + ledger_id + '/effects/'
        return self.query(url, params)

    def ledger_offers(self, ledger_id, params=None):
        url = '/ledgers/' + ledger_id + '/offers/'
        return self.query(url, params)

    def ledger_operations(self, ledger_id, params=None):
        url = '/ledgers/' + ledger_id + '/operations/'
        return self.query(url, params)

    def ledger_payments(self, ledger_id, params=None):
        url = '/ledgers/' + ledger_id + '/payments/'
        return self.query(url, params)

    def effects(self, params=None, sse=False):
        url = '/effects/'
        return self.query(url, params, sse)

    def operations(self, params=None, sse=False):
        url = '/operations/'
        return self.query(url, params, sse)

    def operation(self, op_id, params=None):
        url = '/operations/' + op_id
        return self.query(url, params)

    def operation_effects(self, tx_hash, params=None):
        url = '/operations/' + tx_hash + '/effects/'
        return self.query(url, params)

    def payments(self, params=None, sse=False):
        url = '/payments/'
        return self.query(url, params, sse)

    def assets(self, params=None):
        url = '/assets/'
        return self.query(url, params)

    def _query(self, url, params=None, sse=False):
        if not sse:
            return self._session.get(url, params=params, timeout=self.request_timeout).json()  # TODO: custom exception?

        # SSE connection
        if SSEClient is None:
            raise ValueError('SSE not supported, missing sseclient module')
        if params:
            url = url + '?' + urlencode(params)
        messages = SSEClient(url, session=self._session)
        return messages
        # TODO: reonnect on connection failure

    @staticmethod
    def testnet():
        return Horizon(horizon_uri=HORIZON_TEST)

    @staticmethod
    def livenet():
        return Horizon(horizon_uri=HORIZON_LIVE)


