![Kin Logo](kin.png)

# KIN Python SDK for Kin Blockchain

## Requirements.

Python >= 3.6

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
The KinClient object can be used with a context manager, or closed manually, to close the connection to the blockchain

```python
from kin import KinClient, TEST_ENVIRONMENT

async with KinClient(TEST_ENVIRONMENT) as client:
   ...

OR

client = KinClient(TEST_ENVIRONMENT)
try:
   ...
finally:
   client.close()

```

Custom environment can also be used:  
```python
from kin import Environment

MY_CUSTOM_ENVIRONMENT = Environemnt('name','horizon endpoint','network passphrase','friendbot url'(optional))
```

Once you have a KinClient, you can use it to get a KinAccount object: 
```python
# The KinAccount object can be initizlied in two ways:

# With a single seed:
account = client.kin_account('seed')

# With channels:
account = client.kin_account('seed', channel_secret_keys=['seed1','seed2','seed3'...])

# Additionaly, an unique app-id can be provided, this will mark all of your transactions and allow the Kin Ecosystem to track the kin usage of your app
# A unique app-id should be received from the Kin Ecosystem
account = client.kin_account('seed',app_id='unique_app_id')
```
Read more about channels in the ["Channels" section](#Channels)

## Client Usage
Most methods provided by the KinClient to query the blockchain about a specific account, can also be used from the KinAccount object to query the blockchain about itself

### Getting Account Balance
```python
# Get KIN balance
balance = await client.get_account_balance('address')
```

### Getting Account Data
```python
account_data = await client.get_account_data('address')
```

### Checking If an account exists on the blockchain
```python
await client.does_account_exists('address')
```

### Getting the minimum acceptable fee from the blockchain
Transactions usually require a fee to be processed.
To know what is the minimum fee that the blockchain will accept, use:
```python
minimum_fee = await client.get_minimum_fee()
```

### Getting Transaction Data
Get information about a specific transaction
The 'simple' flag is enabled by default, and dictates what object should be returned
For simple=False: A 'kin.RawTransaction' object will return,
containing some fields that may be confusing and of no use to the user.

For simple=True: A 'kin.SimpleTransaction' object will return,
containing only the data that the user will need.
However, if the transaction if too complex to be simplified, a 'CantSimplifyError' will be raised
```python
tx_data = await sdk.get_transaction_data(tx_hash, simple=True/False)
```


A transaction will not be simplified if:
1. It contains a memo that is not a text memo
2. It contains multiple operations
3. It contains a payment that is not of KIN
4. Its operation type is not one of 'Payment'/'Create account'.

Given the use case of our blockchain, and the tools that we currently provide to interact with it, these conditions should not usually occur.

### Checking configuration
The handy `get_config` method will return some parameters the client was configured with, along with Horizon status:
```python
status = client.get_config()
```

```json
    {
  "sdk_version": "2.4.0",
  "environment": "TEST",
  "horizon": {
    "uri": "https://horizon-testnet.kininfrastructure.com",
    "online": true,
    "error": null
  },
  "transport": {
    "pool_size": 100,
    "num_retries": 3,
    "request_timeout": 11,
    "backoff_factor": 0.5
  }
}
```
- `sdk_version` - the version of this SDK.
- `environment` - the environment the SDK was configured with (TEST/PROD/CUSTOM).
- `horizon`:
  - `uri` - the endpoint URI of the Horizon server.
  - `online` - Horizon online status.
  - `error` - Horizon error (when not `online`) .
- `transport`:
  - `pool_size` - number of pooled connections to Horizon.
  - `num_retries` - number of retries on failed request.
  - `request_timeout` - single request timeout.
  - `backoff_factor` - a backoff factor to apply between retry attempts.


### Friendbot
If a friendbot endpoint is provided when creating the environment (it is provided with the TEST_ENVIRONMENT),
you will be able to use the friendbot method to call a service that will create an account for you
```python
await client.friendbot('address')
```

Additionally, you may also use the friendbot to request KIN for testing
```python
await client.friendbot_fund('address', amount) # Up to 10K KIN
```


## Account Usage

### Getting Wallet Details
Get the public address of my wallet account. The address is derived from the seed the account was created with.
```python
address = account.get_public_address()
```

### Creating a New Account
Create a new account
the KIN amount can be specified in numbers or as a string
```python
tx_hash = await account.create_account('address', starting_balance=1000, fee=100)
```
A text memo can also be provided:
```python
tx_hash = await account.create_account('address', starting_balance=1000, fee=100, memo_text='Account creation')
```

### Sending KIN
The KIN amount can be specified in numbers or as a string
```python
tx_hash = await account.send_kin('destination', 1000, fee=100, memo_text='order123')
```

### Build/Submit transactions
While the previous methods build and send the transaction for you, there is another way to send transactions

Step 1: Build the transaction
```python
builder = account.build_send_kin('destination', 1000, fee=100, memo_text='order123')
```
Step 2: Update the transaction
```python
# do whatever you want with the builder
async with account.channel_manager.get_channel() as channel:
    await builder.set_channel(channel)
    builder.sign(channel)
    # If you used additional channels apart from your main account,
    # sign with your main account
    builder.sign(account.keypair.secret_seed)
```
Step 3: Send the transaction
```python
    tx_hash = await account.submit_transaction(builder)
```

### Whitelist a transaction
Assuming you are registered as a whitelisted digital service with the Kin Ecosystem (exact details TBD)
You will be able to whitelist transactions for your clients, making it so that their fee will not be deducted
Your clients will send an http request to you containing their tx.
You can then whitelist it, and return it back to the client to send to the blockchain
```python
whitelisted_tx = account.whitelist_transaction(client_transaction)

# By defualt, any payment sent from you is already considered whitelisted,
# so there is no need for this step for the server transactions
```

### Get account status
Get the status and config of the account
If verbose it set to true, all channels and statuses will be printed
```python
account.get_status(verbose=False/True)
```

```json
{
  "client": {
    "sdk_version": "2.4.0",
    "environment": "TEST",
    "horizon": {
      "uri": "https://horizon-testnet.kininfrastructure.com",
      "online": true,
      "error": null
    },
    "transport": {
      "pool_size": 100,
      "num_retries": 3,
      "request_timeout": 11,
      "backoff_factor": 0.5
    }
  },
  "account": {
    "app_id": "anon",
    "public_address": "GBQLWHAH5BRB3PTJEXIKGKI3YYM2DJI32ZOZBR4O5WE7FE2GNSUTF6RP",
    "balance": 10000,
    "channels": {
      "total_channels": 5,
      "free_channels": 4,
      "non_free_channels": 1,
      "channels": {
        "SBRHUVGBCXDM2HDSTQ5Y5QLMBCTOTK6GIQ4PDZIMCD3SG3A7MU22ASRV": "free",
        "SA6XIHKGWVGUNOWUPCEA2SWBII5JEHK7Q54I2ESZ42NKUX5NYNXPTA4P": "free",
        "SB57K5N2JUVXBF3S56OND4WXLZAXMBB7WFV5E5ZQTHOGQQTGCY4ZBWGL": "free",
        "SCFXWAXZHM3OJA5XJNW4MIDPRYZHTECXJEOYY5O6JJB523M32OJXD756": "taken",
        "SA6YK4SR2KS2RXV7SN6HFVXNO44AA7IQTZ7QKWAWS6TPJ2NCND2JMLY3": "free"
      }
    }
  }
}
```

## Transactions
These methods are relevant to transactions

### Decode_transaction
When the client sends you a transaction for whitelisting, it will be encoded.
If you wish to decode the transaction and verify its details before whitelisting it:

```python
from kin import decode_transaction

decoded_tx = decode_transaction(encoded_tx)
```

## Keypair
These set of methods allow you to create new keypairs.

### Create a new keypair
```python
from kin import Keypair

my_keypair = Keypair()
```
Or, you can create a keypair from an existing seed
```python
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
Given the same seed and salt, the same seed will always be generated
```python
seed = Keypair.generate_hd_seed('seed','salt')
```

## Monitoring Kin Payments
These methods can be used to monitor the kin payment that an account or accounts is sending/receiving
### Monitor a single account
Monitoring a single account will continuously get data about this account from the blockchain and filter it.
An additional "timeout" parameter can be passed to raise a "TimeoutError" if too much time passes between each tx.
```python
async for tx in client.monitor_account_payments('address'):
   ...
```

### Monitor multiple accounts
Monitoring multiple accounts will continuously get data about **all** accounts on the blockchain, and will filter it to only yield txs for the relevant accounts.
Since this monitor receives a set of addresses, you can freely add/remove address at from it at any point
```python
addresses = set(['address1','address2'])
async for address, tx in client.monitor_accounts_payments(addresses):
   ...
```

## Channels

One of the most sensitive points in Stellar is [transaction sequence](https://www.stellar.org/developers/guides/concepts/transactions.html#sequence-number).
In order for a transaction to be submitted successfully, this number should be correct. However, if you have several 
SDK instances, each working with the same wallet account or channel accounts, sequence collisions will occur. 
 
We highly recommend to keep only one KinAccount instance in your application, having unique channel accounts.
Depending on the nature of your application, here are our recommendations:

1. You have a simple (command line) script that sends transactions on demand or only once in a while. 
In this case, the SDK can be instantiated with only the wallet key, the channel accounts are not necessary.

2. You have a single application server that should handle a stream of concurrent transactions. In this case, 
you need to make sure that only a single instance of a KinAccount initialized with multiple channel accounts.

3. You have a number of load-balanced application servers. Here, each application server should a) have the setup outlined
above, and b) have its own channel accounts. This way, you ensure you will not have any collisions in your transaction
sequences.

### Creating Channels
The kin sdk allows you to create HD (highly deterministic) channels based on your seed and a passphrase to be used as a salt.
As long as you use the same seed and passphrase, you will always get the same seeds.

```
import kin.utils

channels = utils.create_channels(master_seed, environment, amount, starting_balance, salt)

# "channels" will be a list of seeds the sdk created for you, that can be used when initializing the KinAccount object.
```
If you just wish to get the list of the channels generated from your seed + passphrase combination without creating them
```python
channels = utils.get_hd_channels(master_seed, salt, amount)
```


## License
The code is currently released under [Kin Ecosystem SDK License](LICENSE.pdf).


## Contributing
See [CONTRIBUTING.md](CONTRIBUTING.md) for SDK contributing guidelines. 


