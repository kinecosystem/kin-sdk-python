![Kin Logo](kin.png)

# KIN Python SDK for Kin Blockchain


## Disclaimer

The SDK is still in beta. No warranties are given, use on your own discretion.

## Requirements.

Python 2 > 2.7.9 / 3 > 3.4

## Installation 

```bash
pip install kin-sdk
```

## Usage

### Initialization

The sdk has two main components, KinClient and KinAccount.  
**KinClient** - Used to query the blockchain and perform actions that don't require authentication (e.g Get account balance)  
**KinAccount** - Used to perform authenticated actions on the blockchain (e.g Send payment)

To initialize the Kin Client you will need to provide an environment (Test and Production environments are pre-configured)


```python
from kin import KinClient, TEST_ENVIRONMENT

client = KinClient(TEST_ENVIRONMENT)
```

Custom environment can also be used:  
```python
from kin import Environment

MY_CUSTOM_ENVIRONMENT = Environemnt('name','horizon endpoint','network passphrase','kin issuer','friendbot url'(optional))
```

Once you have a KinClient, you can use it to get a KinAccount object: 
```python
# The KinAccount object can be initizlied in a number of ways:

# With a single seed:
account = client.kin_account('seed')

# With specific channels:
account = client.kin_account('seed', channel_secret_keys=['seed1','seed2','seed3'...])

# With deterministic channels
# This will generate the channels secret seeds for you, based on your primary seed. 
# The generated channels will always be the same for the same primary seed.
# If this is your first time using these channels, you should set 'create_channels' to true.
# This will create the channel account from your primary seed (and will cost 1.6 * number of channels XLM)
account = client.kin_account('seed',channels=number, create_channels=True/False)

# Every seed can only send one transaction per ledger (~5 seconds),
# so using channels will greatly increase your concurrency.

# Additionaly, an unique app-id can be provided, this will mark all of your transactions and allow the Kin Ecosystem to track the kin usage of your app
# A unique app-id should be recivied from the Kin Ecosystem
# If no app-id is given, an 'anonymous' app-id will be used
account = client.kin_account('seed',app_id='unique_app_id')
```

## Client Usage
Most methods provided by the KinClient to query the blockchain about a specific account, can also be used from the KinAccount object to query the blockchain about itself

### Getting Account Balance
```python
# Get KIN/XLM balance
balances = client.get_account_balances('address')
kin_balance = balances['KIN']
xlm_balance = balances['XLM']
```

### Getting Account Data
```python
account_data = client.get_account_data('address')
```

### Checking Account Status
```python
from kin import AccountStatuses

status = client.get_account_status('address')

# status can be one of:
AccountStatuses.NOT_CREATED
AccountStatuses.NOT_ACTIVATED
AccountStatuses.ACTIVATED
```


### Getting Transaction Data
```python
# Get information about a specific transaction
# The 'simple' flag is enabled by defualt, and dectates what object should be returned
# For simple=False: A 'kin.TransactionData' object will return,
# containig many fields that may be confusing and of no use to the user.

# For simple=True: A 'kin.SimpleTransaction' object will return,
# containing only the data that the user will need.
# However, if the transaction if too complex to be simplified, a 'CantSimplifyError' will be raised
tx_data = sdk.get_transaction_data(tx_hash, simple=True/False)

# A transaction will not be simplifed if:
# 1. It contains a memo that is not a text memo
# 2. It contains a payment that is not of KIN/XLM
# 3. It contains activation to anything other than KIN
# 4. Its operation type is not one of 'Payment'/'Activation'/'Create account'.

# Given the use case of our blockchain, and the tools that we currently provied to interact with it, these conditions should not occur.
```

### Verify Kin Payment
This method provides an easy way to verify that a transaction is what you expect it to be  
```python
client.verify_kin_payment('tx_hash','sender','destination',amount,memo(optional),check_memo=True/False)

#Lets say that addr1 payed 15 KIN to add2, with the memo 'Enjoy!'

client.verify_kin_payment('tx_hash','addr1','addr2',15,'Enjoy!',True) >> True
client.verify_kin_payment('tx_hash','addr1','addr2',15,'Hello',True) >> False
client.verify_kin_payment('tx_hash','addr1','addr2',15) >> True
client.verify_kin_payment('tx_hash','addr1','addr2',10) >> False
client.verify_kin_payment('tx_hash','addr1','addr3',10) >> False
```

### Getting transaction history
This method allows you to receive a list of transactions that are related to an account
```python
tx_history = client.get_account_transaction_history('address')

# several optional parameters are avilable:
# simple=(True)/False - Should the the resulting transactions be simplified. A transaction that cannot be simplified will be skipped
# descending=(True)/False - The order of the transactions
# cursor=None/Number - A paging token to get a specific transaction list

# Note that currently the maximum amount of tranactions you can get in a single request from the blockchain is 200,
# if the requested amount is bigger than 200, the function will run recursivly until it got the requested amount
```

### Checking configuration
The handy `get_config` method will return some parameters the client was configured with, along with Horizon status:
```python
status = client.get_config()
print status
{
  "horizon": {
    "uri": "https://horizon-playground.kininfrastructure.com",
    "online": true,
    "error": null
  },
  "sdk_version": "2.0.0",
  "environment": "PLAYGROUND",
  "kin_asset": {
    "code": "KIN",
    "issuer": "GBC3SG6NGTSZ2OMH3FFGB7UVRQWILW367U4GSOOF4TFSZONV42UJXUH7"
  },
  "transport": {
    "pool_size": 10,
    "request_timeout": 11,
    "backoff_factor": 0.5,
    "num_retries": 5,
    "retry_statuses": [
      503,
      413,
      429,
      504
    ]
  }
}
```
- `sdk_version` - the version of this SDK.
- `address` - the SDK wallet address.
- `kin_asset` - the KIN asset the SDK was configured with.
- `environment` - the environment the SDK was configured with (TEST/PROD/CUSTOM).
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


### Friendbot
```python
# If a friendbot endpoint is provided when creating the environment (it is provided with the TEST_ENVIRONMENT),  
# you will be able to use the friendbot method to call a service that will create an account for you

client.friendbot('address')
```

### Activate Account
**This is the only KinClient method that requires a seed**
```python
client.activate_account('seed')
```


## Account Usage

### Getting Wallet Details
```python
# Get the public address of my wallet account. The address is derived from the seed the account was inited with.
address = account.get_public_address()
```

### Creating a New Account
```python
# create a new account prefunded with MIN_ACCOUNT_BALANCE XLM
tx_hash = account.create_account('address')

# create a new account prefunded with a specified amount of XLM.
tx_hash = account.create_account('address', starting_balance=1000)

# a text memo can also be provided:
# the text memo can fit up to 21 bytes of utf-8 text
tx_hash = account.create_account('address', starting_balance=1000,memo_text='Account creation example')

# Note:
# By defualt, created accounts are also activated on creation,
this can be overriden by setting the 'activate' falg to False

tx_hash = account.create_account('address', activate=False)
```

### Sending Currency
```python
# send XLM
tx_hash = account.send_xlm('address', 100, memo_text='order123')

# send KIN
tx_hash = account.send_kin('address', 1000, memo_text='order123')
```

### Build/Submit transactions
While the previous methods build and send the transaction for you, there is another way to send transactions with two steps

Step 1: Build the transaction
```python
tx = account.build_send_kin('address',100,memo_text='order123')
```
Step 2: Submit the transaction
```python
tx_hash = account.submit_transaction(tx)
```

This can be useful for some advanced use cases, since the 'build' methods return a 'kin.Transaction' object.
The transaction object can give you the tx_hash of the transaction before sending it, and can be used to perform advanced operations such as multi-signature/multi-operations **(Not implemented yet)**

**Pay attention** - Building a tx locks a channel for this specific transaction, submiting it releases that lock. However if you wish to build a tx, but decide not to submit it, make sure to release this lock with
```python
tx.release()
```

## Keypair
These set of methods allow you to create new keypairs.

### Create a new keypair
```python
from kin import Keypair

my_keypair = Keypair()
# Or, you can create a keypair from an existing seed
my_keypair = Keypair('seed')
```

### Getting the public address from a seed
```python
public_address = Keypair.address_from_seed('seed')
```

### Generate a new random seed
```python
seed = Keypair.generate_seed()
```

### Generate a deterministic seed
```python
# Given the same seed and salt, the same seed will always be generated
seed = Keypair.generate_hd_seed('seed','salt')
```

### Generate a mnemonic seed:
**Not implemented yet**

## Monitoring Kin Payments
These methods can be used to monitor the kin payment that an account or accounts is sending/receiving  
**Currently, due to a bug on the blockchain frontend, the monitor may also return 1 tx that happened before the monitoring request**


The monitor will run in a background thread (accessible via ```monitor.thead```) ,   
and will call the callback function everytime it finds a kin payment for the given address.
### Monitor a single account
Monitoring a single account will continuously get data about this account from the blockchain and filter it.

```python
def callback_fn(address, tx_data, monitor)
	print ('Found tx: {} for address: {}'.format(address,tx_data.id))
    
monitor = client.monitor_account_payments('address', callback_fn)
```

### Monitor multiple accounts
Monitoring multiple accounts will continuously get data about **all** accounts on the blockchain, and will filter it.

```python
def callback_fn(address, tx_data, monitor)
	print ('Found tx: {} for address: {}'.format(address,tx_data.id))
    
monitor = client.monitor_accounts_payments(['address1','address2'], callback_fn)
```

You can freely add or remove accounts to this monitor

```python
monitor.add_address('address3')
monitor.remove_address('address1')
```

### Stopping a monitor
When you are done monitoring, make sure to stop the monitor, to terminate the thread and the connection to the blockchain.

```python
monitor.stop()
```

## Limitations

One of the most sensitive points in Stellar is [transaction sequence](https://www.stellar.org/developers/guides/concepts/transactions.html#sequence-number).
In order for a transaction to be submitted successfully, this number should be correct. However, if you have several 
SDK instances, each working with the same wallet account or channel accounts, sequence collisions will occur. 
 
We highly recommend to keep only one KinAccount instance in your application, having unique channel accounts.
Depending on the nature of your application, here are our recommendations:

1. You have a simple (command line) script that sends transactions on demand or only once in a while. 
In this case, the SDK can be instantiated with only the wallet key, the channel accounts are not necessary.

2. You have a single application server that should handle a stream of concurrent transactions. In this case, 
you need to make sure that only a single instance of a KinAccount initialized with multiple channel accounts. 
This is an important point, because if you use a standard `gunicorn/Flask` setup for example, gunicorn will spawn 
several *worker processes*, each containing your Flask application, each containing your KinAccount instance, so multiple
KinAccount instances will exist, having the same channel accounts. The solution is to use gunicorn *thread workers* instead of
*process workers*, for example run gunicorn with `--threads` switch instead of `--workers` switch, so that only 
one Flask application is created, containing a single KinAccount instance.

3. You have a number of load-balanced application servers. Here, each application server should a) have the setup outlined
above, and b) have its own channel accounts. This way, you ensure you will not have any collisions in your transaction
sequences.


## License
The code is currently released under [MIT license](LICENSE).


## Contributing
See [CONTRIBUTING.md](CONTRIBUTING.md) for SDK contributing guidelines. 


