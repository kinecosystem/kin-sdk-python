![Kin Logo](kin.png)  ![Stelalr Logo](stellar.png)

# KIN Python SDK for Stellar Blockchain
[![Build Status](https://travis-ci.org/kinecosystem/kin-core-python.svg?branch=master)](https://travis-ci.org/kinecosystem/kin-core-python) [![Coverage Status](https://codecov.io/gh/kinecosystem/kin-core-python/branch/master/graph/badge.svg)](https://codecov.io/gh/kinecosystem/kin-core-python)

## Disclaimer

The SDK is still in beta. No warranties are given, use on your own discretion.

## Requirements.

Make sure you have Python 2 >=2.7.9.

## Installation 

```bash
pip install git+https://github.com/kinecosystem/kin-core-python.git
```

## Usage

### Initialization

To initialize the SDK, you need to provide the following parameters:
- (optional) the secret key to init the internal SDK wallet with. If not provided, you will NOT be able to use the 
  following functions: `get_address`, `get_native_balance`, `get_kin_balance`, `create_account`, `monitor_kin_payments`.
- (optional) the endpoint URI of your [Horizon](https://www.stellar.org/developers/horizon/reference/) node. 
  If not provided, a default Horizon endpoint will be used, either a testnet or pubnet, depending on the `network` 
  parameter below.
- (optional) a network identifier, which is either `PUBLIC` or `TESTNET`, defaults to `PUBLIC`.
- (optional) a list of channel keys. If provided, the channel accounts will be used to sign transactions instead 
  of the internal SDK wallet. Use it to insure higher concurrency.


```python
import kin

# Init SDK without a secret key, in the public Stellar network (for generic blockchain queries)
sdk = kin.SDK()

# Init SDK without a secret key, for Stellar testnet
sdk = kin.SDK(network='TESTNET')

# Init SDK without a secret key, with specific Horizon server, running on Stellar testnet
sdk = kin.SDK(horizon_endpoint_uri='http://my.horizon.uri', network='TESTNET')

# Init SDK with wallet secret key, on public network
sdk = kin.SDK(secret_key='my key')

# Init SDK with several channels, on public network
sdk = kin.SDK(secret_key='my key', channel_secret_keys=['key1', 'key2', ...])
```
For more examples, see the [SDK test file](test/test_sdk.py).


### Getting Wallet Details
```python
# Get the address of my wallet account. The address is derived from the secret key the SDK was inited with.
address = sdk.get_address()
```

### Getting Account Balance
```python
# Get native (lumen) balance of the SDK wallet
native_balance = sdk.get_native_balance()

# Get KIN balance of the SDK wallet
kin_balance = sdk.get_kin_balance()

# Get native (lumen) balance of some account
native_balance = sdk.get_account_native_balance('address')

# Get KIN balance of some account
kin_balance = sdk.get_account_kin_balance('address')
```

### Getting Account Data
```python
# returns kin.AccountData
account_data = sdk.get_account_data('address')
```

### Checking If Account Exists
```python
account_exists = sdk.check_account_exists('address')
```

### Creating a New Account
```python
# create a new account prefunded with MIN_ACCOUNT_BALANCE lumens
tx_hash = sdk.create_account('address')

# create a new account prefunded with a specified amount of native currency (lumens).
tx_hash = sdk.create_account('address', starting_balance=1000)

# create a new activated account
tx_hash = sdk.create_account('address', starting_balance=1000,activate=True)  
```
### Checking if Account is Activated (Trustline established)
```python
# check if KIN is trusted by some account
kin_trusted = sdk.check_account_activated('address')
```

### Sending Currency
```python
# send native currency (lumens) to some address
tx_hash = sdk.send_native('address', 100, memo_text='order123')

# send KIN to some address
tx_hash = sdk.send_kin('address', 1000, memo_text='order123')
```

### Getting Transaction Data
```python
# create a transaction, for example a new account
tx_hash = sdk.create_account('address')
# get transaction data, returns kin.TransactionData
tx_data = sdk.get_transaction_data(tx_hash)
```

### Transaction Monitoring
```python
# define a callback function that receives an address and a kin.TransactionData object
def print_callback(address, tx_data):
    print(address, tx_data)
    
# start monitoring KIN payments related to the SDK wallet account
sdk.monitor_kin_payments(print_callback)

# start monitoring KIN payments related to a list of addresses
sdk.monitor_accounts_kin_payments(['address1', 'address2'], print_callback)

# start monitoring all transactions related to a list of addresses
sdk.monitor_accounts_transactions(['address1', 'address2'], print_callback)
```

#### Receiving Payments from Users
Let us consider a real-life case when you need to receive payments from users for the orders they make.
In order to associate a transaction with an order, we will use the `TransactionData.memo` field:

```python
# setup your orders cache
orders = {}

# define a callback function that validates payments and marks orders as completed
def payment_callback(address, tx_data):
    order_id = tx_data.memo
    if order_id not in orders:
        logging.warn('order not found: {}'.format(order_id))
        return
    
    order = orders[order_id]
    
    # check that the order is not yet completed
    if order['completed'] is not None:
        logging.warn('order {} is already completed'.format(order_id))
        return
        
    # check that the amount matches 
    if tx_data.operations[0].amount != order['amount']:
        logging.warn('wrong amount paid for order {}: received {}, need {}'
            .format(order_id, tx_data.operations[0].amount, order['amount']))
        return
        
    # all good
    order['completed'] = datetime.now()


# start monitoring KIN payments related to the SDK wallet account
sdk.monitor_kin_payments(payment_callback)   

# when an order comes, store its data in the cache
order_id = generate_order_id()
orders[order_id] = {
    'user_id': user_id,
    'product_id': product_id,
    'amount': product_cost,
    'created': datetime.now(),
    'completed': None
}

# now pass this order_id to the user and have him insert it into the memo field of his transaction.
# After he submits the transaction, the payment_callback above will catch it and update the order data.
```

### Checking Status
The handy `get_status` method will return some parameters the SDK was configured with, along with Horizon status:
```python
status = sdk.get_status()
print status
#  {
#     'sdk_version': '0.2.0',
#     'channels': {
#         'all': 5,  
#         'free': 5  
#     }, 
#     'kin_asset': {
#         'code': 'KIN', 
#         'issuer': '<issuer address>'
#     }, 
#     'network': 'TESTNET', 
#     'horizon': {
#         'uri': '<horizon uri>', 
#         'online': True,
#         'error': None 
#     }, 
#     'address': '<sdk wallet address>',
#     'transport': {
#         'pool_size': 7,
#         'num_retries': 5,
#         'request_timeout': 11,
#         'retry_statuses': [413, 429, 503, 504],
#         'backoff_factor': 0.5
#     }
#   }
```
- `sdk_version` - the version of this SDK.
- `address` - the SDK wallet address.
- `channels`:
  - `all` - the number of channels the SDK was configured with.
  - `free` - the number of currently free channels. If the number is consistently close to zero, it means the channels
             are always busy, and you might consider adding more channels or more servers.
- `kin_asset` - the KIN asset the SDK was configured with.
- `network` - the network the SDK was configured with (PUBLIC/TESTNET/CUSTOM).
- `horizon`:
  - `uri` - the endpoint URI of the Horizon server.
  - `online` - Horizon online status.
  - `error` - Horizon error (when not `online`) .
- `transport`:
  - `pool_size` - number of pooled connections to Horizon.
  - `num_retries` - number of retries on failed request.
  - `request_timeout` - single request timeout.
  - `retry_statuses` - a list of statuses to retry on.
  - `backoff_factor` - a backoff factor to apply between retry attempts.


## Limitations

One of the most sensitive points in Stellar is [transaction sequence](https://www.stellar.org/developers/guides/concepts/transactions.html#sequence-number).
In order for a transaction to be submitted successfully, this number should be correct. However, if you have several 
SDK instances, each working with the same wallet account or channel accounts, sequence collisions will occur. 
Though the SDK makes an effort to retrieve the correct sequence and retry the transaction, this is not a recommended practice. 
Instead, we highly recommend to keep only one SDK instance in your application, having unique channel accounts.
Depending on the nature of your application, here are our recommendations:

1. You have a simple (command line) script that sends transactions on demand or only once in a while. 
In this case, the SDK can be instantiated with only the wallet key, the channel accounts are not necessary.

2. You have a single application server that should handle a stream of concurrent transactions. In this case, 
you need to make sure that only a single instance of SDK is initialized with multiple channel accounts. 
This is an important point, because if you use a standard `gunicorn/Flask` setup for example, gunicorn will spawn 
several *worker processes*, each containing your Flask application, each containing your SDK instance, so mutliple
SDK instances will exist, having the same channel accounts. The solution is to use gunicorn *thread workers* instead of
*process workers*, for example run gunicorn with `--threads` switch instead of `--workers` switch, so that only 
one Flask application is created, containing a single SDK instance.

3. You have a number of load-balanced application servers. Here, each application server should a) have the setup outlined
above, and b) have its own channel accounts. This way, you ensure you will not have any collisions in your transaction
sequences.


## License
The code is currently released under [MIT license](LICENSE).


## Contributing
See [CONTRIBUTING.md](CONTRIBUTING.md) for SDK contributing guidelines. 

