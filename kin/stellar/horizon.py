# -*- coding: utf-8 -*

# Copyright (C) 2018 Kin Foundation

import requests
from requests.adapters import HTTPAdapter, DEFAULT_POOLSIZE
import sys
from urllib3.util import Retry

from stellar_base.horizon import HORIZON_LIVE, HORIZON_TEST

from .errors import HorizonError

try:
    from sseclient import SSEClient
except ImportError:
    SSEClient = None

if sys.version[0] == '2':
    from urllib import urlencode
else:
    # noinspection PyUnresolvedReferences
    from urllib.parse import urlencode


DEFAULT_REQUEST_TIMEOUT = 60  # one minute, see github.com/stellar/horizon/txsub/system.go#L223
DEFAULT_NUM_RETRIES = 5
DEFAULT_BACKOFF_FACTOR = 0.5
USER_AGENT = 'py-stellar-base'


class Horizon(object):
    """
    This class redefines :class:`~stellar_base.horizon.Horizon` to provide additional functionality.
    """
    def __init__(self, horizon_uri=None, pool_size=DEFAULT_POOLSIZE, num_retries=DEFAULT_NUM_RETRIES,
                 request_timeout=DEFAULT_REQUEST_TIMEOUT, backoff_factor=DEFAULT_BACKOFF_FACTOR, user_agent=USER_AGENT):
        if horizon_uri is None:
            self.horizon_uri = HORIZON_TEST
        else:
            self.horizon_uri = horizon_uri

        self.request_timeout = request_timeout

        # init transport adapter
        retry = Retry(total=num_retries, backoff_factor=backoff_factor, redirect=0)
        adapter = HTTPAdapter(pool_connections=1, pool_maxsize=pool_size, max_retries=retry)

        # init session
        session = requests.Session()

        # set default headers
        session.headers.update({'User-Agent': user_agent})

        session.mount('http://', adapter)
        session.mount('https://', adapter)
        self._session = session

    def submit(self, te):
        params = {'tx': te}
        url = self.horizon_uri + '/transactions/'
        reply = self._session.post(url, data=params, timeout=self.request_timeout)
        try:
            reply_json = reply.json()
        except ValueError:
            raise Exception('invalid horizon reply: [{}] {}'.format(reply.status_code, reply.text))
        return check_horizon_reply(reply_json)

    def query(self, rel_url, params=None, sse=False):
        abs_url = self.horizon_uri + rel_url
        reply = self._query(abs_url, params, sse)
        return check_horizon_reply(reply) if not sse else reply

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

    def trades(self, params=None):
        url = '/trades/'
        return self.query(url, params)

    def ledgers(self, params=None, sse=False):
        url = '/ledgers/'
        return self.query(url, params, sse)

    def ledger(self, ledger_id):
        url = '/ledgers/' + str(ledger_id)
        return self.query(url)

    def ledger_effects(self, ledger_id, params=None):
        url = '/ledgers/' + str(ledger_id) + '/effects/'
        return self.query(url, params)

    def ledger_operations(self, ledger_id, params=None):
        url = '/ledgers/' + str(ledger_id) + '/operations/'
        return self.query(url, params)

    def ledger_payments(self, ledger_id, params=None):
        url = '/ledgers/' + str(ledger_id) + '/payments/'
        return self.query(url, params)

    def effects(self, params=None, sse=False):
        url = '/effects/'
        return self.query(url, params, sse)

    def operations(self, params=None, sse=False):
        url = '/operations/'
        return self.query(url, params, sse)

    def operation(self, op_id, params=None):
        url = '/operations/' + str(op_id)
        return self.query(url, params)

    def operation_effects(self, op_id, params=None):
        url = '/operations/' + str(op_id) + '/effects/'
        return self.query(url, params)

    def payments(self, params=None, sse=False):
        url = '/payments/'
        return self.query(url, params, sse)

    def assets(self, params=None):
        url = '/assets/'
        return self.query(url, params)

    def _query(self, url, params=None, sse=False):
        if not sse:
            return self._session.get(url, params=params, timeout=self.request_timeout).json()

        # SSE connection
        if SSEClient is None:
            raise ValueError('SSE not supported, missing sseclient module')

        last_id = None
        if params:
            if 'last_id' in params:
                last_id = params['last_id']
                del params['last_id']
            url = url + '?' + urlencode(params)
        return SSEClient(url, last_id=last_id, session=self._session)

    @staticmethod
    def testnet():
        return Horizon(horizon_uri=HORIZON_TEST)

    @staticmethod
    def livenet():
        return Horizon(horizon_uri=HORIZON_LIVE)


def check_horizon_reply(reply):
    if 'status' not in reply:
        return reply
    raise HorizonError(reply)
