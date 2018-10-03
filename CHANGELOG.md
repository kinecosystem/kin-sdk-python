## kin-core-python v1>v2 changelog:

* Created environment class to simplify initialization and to bypass 'hack' we used to work on our private blockchain
* An "Environment" must be specified on initialization, Public stellar blockchain is no longer the default
* Changed get_status to get_config
* Separate SDK to 2 components, 'KinAccount' and 'KinClient'
* get_config now only shows info about the KinClient, and not the KinAccount
* Separated account monitoring to monitoring single or multiple accounts.
* Monitors now call the callback method twice if both the source and destination are watched
* Account monitoring can now be stopped.
* Expose the thread the monitor is running in, to allow for methods like ```.join()```
* Added ability to add/remove addresses to watch to an existing monitor
* Callback method now receives the monitor itself, to allow monitor stopping from the callback context.
* Added friendbot functionality
* Raise exception when the amount is too precise (returned empty exception before)
* Created a 'SimpleTransaction' and 'SimpleOperation' models to simplify tx data shown to the user.
* get_address renamed to get_public_address
* Added activate account method (change_trust operation)
* Added verify kin payment method
* Using Float instead of Decimal for amounts when getting tx data
* Automatically top-up channels that are out of XLM
* Tests now run on our own docker environment from the blockchain-ops repo
* Added ability to create keypairs
* Added ability to automatically create channels for the user
* Raise an exception if the memo is too long (previously the SDK just trimmed it to fit 28 characters)
* Added ability to build tx before sending it (or without sending it at all)
* Added our default environments (Playground & Ecosystem)
* Removed ability to work with an asset not called KIN
* Removed ability to monitor non-KIN payments
* Fix a bug that caused the sdk to never retry http requests

Please read the new [README](https://github.com/kinecosystem/kin-core-python/blob/v2-master/README.md) to see the new methods explained in details, and examples on how to use the sdk for common use cases