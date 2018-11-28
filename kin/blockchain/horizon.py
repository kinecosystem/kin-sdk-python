"""Contains the Horizon class to interact with horizon"""

import requests
from requests.adapters import HTTPAdapter, DEFAULT_POOLSIZE
from requests.exceptions import RequestException
import sys
from time import sleep
from urllib3.util import Retry

from kin_base.horizon import HORIZON_LIVE, HORIZON_TEST

from .errors import HorizonError

import logging

logger = logging.getLogger(__name__)

try:
    from sseclient import SSEClient
except ImportError:
    SSEClient = None

if sys.version[0] == '2':
    # noinspection PyUnresolvedReferences
    from urllib import urlencode
else:
    # noinspection PyUnresolvedReferences
    from urllib.parse import urlencode

DEFAULT_REQUEST_TIMEOUT = 11  # two ledgers + 1 sec, let's retry faster and not wait 60 secs.
DEFAULT_NUM_RETRIES = 5
DEFAULT_BACKOFF_FACTOR = 0.5
USER_AGENT = 'py-stellar-base'


class Horizon(object):
    """
    This class redefines :class:`kin_base.horizon.Horizon` to provide additional functionality:
        - persistent connection to Horizon and connection pool
        - configurable request retry functionality
        - Horizon error checking and deserialization
    """

    def __init__(self, horizon_uri=None, pool_size=DEFAULT_POOLSIZE, num_retries=DEFAULT_NUM_RETRIES,
                 request_timeout=DEFAULT_REQUEST_TIMEOUT, backoff_factor=DEFAULT_BACKOFF_FACTOR, user_agent=USER_AGENT):
        if horizon_uri is None:
            self.horizon_uri = HORIZON_TEST
        else:
            self.horizon_uri = horizon_uri

        self.pool_size = pool_size
        self.num_retries = num_retries
        self.request_timeout = request_timeout
        self.backoff_factor = backoff_factor

        # adding 504 to the list of statuses to retry
        self.status_forcelist = list(Retry.RETRY_AFTER_STATUS_CODES)
        self.status_forcelist.append(504)

        # configure standard session

        # configure retry handler
        retry = Retry(total=self.num_retries, backoff_factor=self.backoff_factor, redirect=0,
                      status_forcelist=self.status_forcelist)
        # init transport adapter
        adapter = HTTPAdapter(pool_connections=self.pool_size, pool_maxsize=self.pool_size, max_retries=retry)

        # init session
        session = requests.Session()

        # set default headers
        session.headers.update({'User-Agent': user_agent})

        session.mount('http://', adapter)
        session.mount('https://', adapter)
        self._session = session

        # configure SSE session (differs from our standard session)

        sse_retry = Retry(total=1000000, redirect=0, status_forcelist=self.status_forcelist)
        sse_adapter = HTTPAdapter(pool_connections=self.pool_size, pool_maxsize=self.pool_size, max_retries=sse_retry)
        sse_session = requests.Session()
        sse_session.headers.update({'User-Agent': user_agent})
        sse_session.mount('http://', sse_adapter)
        sse_session.mount('https://', sse_adapter)
        self._sse_session = sse_session

    def submit(self, te):
        """Submit the transaction using a pooled connection, and retry on failure."""
        params = {'tx': te}
        url = self.horizon_uri + '/transactions/'

        # POST is not included in Retry's method_whitelist for a good reason.
        # our custom retry mechanism follows
        reply = None
        retry_count = self.num_retries
        while True:
            try:
                reply = self._session.post(url, data=params, timeout=self.request_timeout)
                return check_horizon_reply(reply.json())
            except (RequestException, ValueError) as e:
                if reply:
                    msg = 'horizon submit exception: {}, reply: [{}] {}'.format(str(e), reply.status_code, reply.text)
                else:
                    msg = 'horizon submit exception: {}'.format(str(e))
                logging.warning(msg)

                if reply and reply.status_code not in self.status_forcelist:
                    raise Exception('invalid horizon reply: [{}] {}'.format(reply.status_code, reply.text))
                # retry
                if retry_count <= 0:
                    raise
                retry_count -= 1
                logging.warning('submit retry attempt {}'.format(retry_count))
                sleep(self.backoff_factor)

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

    def ledger_transactions(self, ledger_id, params=None):
        url = '/ledgers/' + str(ledger_id) + '/transactions/'
        return self.query(url, params)

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
            reply = self._session.get(url, params=params, timeout=self.request_timeout)
            try:
                return reply.json()
            except ValueError:
                raise Exception('invalid horizon reply: [{}] {}'.format(reply.status_code, reply.text))

        # SSE connection
        if SSEClient is None:
            raise ValueError('SSE not supported, missing sseclient module')

        return SSEClient(url, session=self._sse_session, params=params)

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
