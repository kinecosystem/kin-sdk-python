# kin-sdk-stellar-python
[![Build Status](https://travis-ci.org/kinfoundation/kin-sdk-stellar-python.svg?branch=master)](https://travis-ci.org/kinfoundation/kin-sdk-stellar-python) [![Coverage Status](https://codecov.io/gh/kinfoundation/kin-sdk-stellar-python/branch/master/graph/badge.svg)](https://codecov.io/gh/kinfoundation/kin-sdk-stellar-python)

KIN Python SDK for Stellar Blockchain

## Disclaimer

The SDK is still in beta. No warranties are given, use on your own discretion.

## Requirements.

Make sure you have Python 2 >=2.7.9.

## Installation 

```bash
pip install git+https://github.com/kinfoundation/kin-sdk-stellar-python.git
```

## Usage

### Initialization

To initialize the SDK, you need to provide the following parameters:
- (optionally) the seed to init the internal SDK wallet with. If not provided, you will NOT be able to use the 
  following functions: `get_address`, `get_lumen_balance`, `get_kin_balance`, `create_account`, `trust_asset`,
  `send_asset`, `monitor_transactions`.
- (optionally) the endpoint URI of your [Horizon](https://www.stellar.org/developers/horizon/reference/) node. 
  If not provided, a default Horizon endpoint will be used,either a testnet or pubnet, depending on the `network` 
  parameter below.
- (optionally) a network identifier, which is either `PUBLIC` or `TESTNET`, defaults to `PUBLIC`.
- (optionally) a list of channel seeds. If provided, the channel accounts will be used to sign transactions instead 
  of the internal SDK wallet.


```python
import kin

# Init SDK without a seed, in the public Stellar network (for generic blockchain queries)
sdk = kin.SDK()

# Init SDK without a seed, for Stellar testnet
sdk = kin.SDK(network='TESTNET')

# Init SDK without a seed, with specific Horizon server, running on Stellar testnet
sdk = kin.SDK(horizon_endpoint_uri='http://my.horizon.uri', network='TESTNET')

# Init SDK with wallet seed, on public network
sdk = kin.SDK(seed='my seed')

# Init SDK with several channels, on public network
sdk = kin.SDK(seed='my seed', channel_seeds=['seed1', 'seed2', ...])
```
For more examples, see the [SDK test file](test/test_sdk.py).


### Getting Wallet Details
```python
# Get the address of my wallet account. The address is derived from the seed the SDK was inited with.
address = sdk.get_address()
```

### Getting Account Balance
```python
# Get lumen balance of the SDK wallet
lumen_balance = sdk.get_lumen_balance()

# Get KIN balance of the SDK wallet
kin_balance = sdk.get_kin_balance()

# Get lumen balance of some address
lumen_balance = sdk.get_address_lumen_balance('address')

# Get KIN balance of some address
kin_balance = sdk.get_address_kin_balance('address')

# Get asset balance of some address
from stellar_base.asset import Asset
my_asset = Asset('XYZ', 'asset issuer address')
asset_balance = sdk.get_address_asset_balance('address', my_asset)
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

# create a new account prefunded with a specified amount of lumens
tx_hash = sdk.create_account('address', starting_balance=1000)
```

### Establishing a Trustline from SDK wallet to some Asset
```python
my_asset = Asset('XYZ', 'asset issuer address')
tx_hash = sdk.trust_asset(my_asset, limit=1000)
```

### Checking Asset Trustline
```python
# check if KIN is trusted by some account
kin_trusted = sdk.check_kin_trusted('address')

# check if some asset is trusted by some account
my_asset = Asset('XYZ', 'asset issuer address')
asset_trusted = sdk.check_asset_trusted('address', my_asset)
```

### Sending Assets
```python
# send lumens to some address
tx_hash = sdk.send_lumens('address', 100, memo_text='order123')

# send KIN to some address
tx_hash = sdk.send_kin('address', 1000, memo_text='order123')

# send some asset to some address
my_asset = Asset('XYZ', 'asset issuer address')
tx_hash = sdk.send_asset('address', my_asset, 100, memo_text='order123')
```

### Getting Transaction Data
```python
# create a transaction, for example a new account
tx_hash = sdk.create_account('address')
# returns kin.TransactionData
tx_data = sdk.get_transaction_data(tx_hash)
```

### Transaction Monitoring
```python
# define a callback function that receives a kin.TransactionData object
def print_callback(tx_data):
    print(tx_data)
    
# start monitoring transactions related to the SDK wallet account
sdk.monitor_transactions(print_callback)

# start monitoring transactions related to some account
sdk.monitor_address_transactions('address', print_callback)
```

## Limitations


## License
The code is currently released under [MIT license](LICENSE).


## Contributing
See [CONTRIBUTING.md](CONTRIBUTING.md) for SDK contributing guidelines. 

