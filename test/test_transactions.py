import pytest

import json
from kin.transactions import SimplifiedTransaction, RawTransaction
from kin.errors import CantSimplifyError


def test_success():
    horizon_resp = json.loads("""{
  "memo": "1-p365-",
  "_links": {
    "self": {
      "href": "http://horizon-testnet.kininfrastructure.com/transactions/f5f16843e1e6160f05bf1cf312ba9328c108b8f0077e36cbe1fad47585352d34"
    },
    "account": {
      "href": "http://horizon-testnet.kininfrastructure.com/accounts/GAUQAOFUVDI65TVONQG2YEJCDZIVK2ZI7LR4ZOS4UCYBADDLI3KVCKSX"
    },
    "ledger": {
      "href": "http://horizon-testnet.kininfrastructure.com/ledgers/826170"
    },
    "operations": {
      "href": "http://horizon-testnet.kininfrastructure.com/transactions/f5f16843e1e6160f05bf1cf312ba9328c108b8f0077e36cbe1fad47585352d34/operations{?cursor,limit,order}",
      "templated": true
    },
    "effects": {
      "href": "http://horizon-testnet.kininfrastructure.com/transactions/f5f16843e1e6160f05bf1cf312ba9328c108b8f0077e36cbe1fad47585352d34/effects{?cursor,limit,order}",
      "templated": true
    },
    "precedes": {
      "href": "http://horizon-testnet.kininfrastructure.com/transactions?order=asc\u0026cursor=3548373130940416"
    },
    "succeeds": {
      "href": "http://horizon-testnet.kininfrastructure.com/transactions?order=desc\u0026cursor=3548373130940416"
    }
  },
  "id": "f5f16843e1e6160f05bf1cf312ba9328c108b8f0077e36cbe1fad47585352d34",
  "paging_token": "3548373130940416",
  "hash": "f5f16843e1e6160f05bf1cf312ba9328c108b8f0077e36cbe1fad47585352d34",
  "ledger": 826170,
  "created_at": "2019-06-19T11:55:15Z",
  "source_account": "GAUQAOFUVDI65TVONQG2YEJCDZIVK2ZI7LR4ZOS4UCYBADDLI3KVCKSX",
  "source_account_sequence": "3035893338210306",
  "fee_paid": 100,
  "operation_count": 1,
  "envelope_xdr": "AAAAACkAOLSo0e7OrmwNrBEiHlFVayj648y6XKCwEAxrRtVRAAAAZAAKySEAAAACAAAAAAAAAAEAAAAHMS1wMzY1LQAAAAABAAAAAQAAAABZg0A36c/vVaXtIHLOVKKAOziSFWIDM70wzmS0plBHqQAAAAAAAAAAZ4DxTkLiA5bx7NU4iIPlrU3eTJI2uFTqzwBDpvlSL0QAAAAAAAAAAAAAAAAAAAACa0bVUQAAAEALIlA0XpHSIDQg1af6WKWyd5pseIKzJMtUlzzJuZ4Gduf14J7Uyh2rcOhsf8xJ9P1+p2wPET7sBPjcynNr44IPplBHqQAAAECZGfeLP6rHRqWmiRy02qdM8ZKgl5rgSto3eHGqxA9rEu3oEtw8lliprpjlornrDQ6lFbJ1wNdV7H5pEZy6laMK",
  "result_xdr": "AAAAAAAAAAAAAAAAAAAAAQAAAAAAAAAAAAAAAAAAAAA=",
  "result_meta_xdr": "AAAAAAAAAAEAAAADAAAAAAAMmzoAAAAAAAAAAGeA8U5C4gOW8ezVOIiD5a1N3kySNrhU6s8AQ6b5Ui9EAAAAAAAAAAAADJs6AAAAAAAAAAAAAAAAAAAAAAAAAAABAAAAAAAAAAAAAAAAAAAAAAAAAwAMmzUAAAAAAAAAAFmDQDfpz+9Vpe0gcs5UooA7OJIVYgMzvTDOZLSmUEepAAAA15QnsUwAAAIXAAALVAAAAAAAAAAAAAAAAAAAAAABAAAAAAAAAAAAAAAAAAAAAAAAAQAMmzoAAAAAAAAAAFmDQDfpz+9Vpe0gcs5UooA7OJIVYgMzvTDOZLSmUEepAAAA15QnsUwAAAIXAAALVAAAAAAAAAAAAAAAAAAAAAABAAAAAAAAAAAAAAAAAAAA",
  "fee_meta_xdr": "AAAAAgAAAAMACskiAAAAAAAAAAApADi0qNHuzq5sDawRIh5RVWso+uPMulygsBAMa0bVUQAAAAAAAAAAAArJIQAAAAEAAAAAAAAAAAAAAAAAAAAAAQAAAAAAAAAAAAAAAAAAAAAAAAEADJs6AAAAAAAAAAApADi0qNHuzq5sDawRIh5RVWso+uPMulygsBAMa0bVUQAAAAAAAAAAAArJIQAAAAIAAAAAAAAAAAAAAAAAAAAAAQAAAAAAAAAAAAAAAAAAAA==",
  "memo_type": "text",
  "signatures": [
    "CyJQNF6R0iA0INWn+lilsneabHiCsyTLVJc8ybmeBnbn9eCe1Modq3DobH/MSfT9fqdsDxE+7AT43Mpza+OCDw==",
    "mRn3iz+qx0alpokctNqnTPGSoJea4EraN3hxqsQPaxLt6BLcPJZYqa6Y5aK56w0OpRWydcDXVex+aRGcupWjCg=="
  ]
}
""")
    tx = SimplifiedTransaction(RawTransaction(horizon_resp))
    assert tx
    # Content of the tx already checked in test_client.test_get_transaction_data


def test_cant_simplify_type():
    horizon_resp = {'envelope_xdr': 'AAAAACkAOLSo0e7OrmwNrBEiHlFVayj648y6XKC'
                                    'wEAxrRtVRAAAAZAAKySEAAAADAAAAAQAAAAAAAA'
                                    'AAAAAAAAAAAAAAAAAAAAAAAQAAAAAAAAAKAAAAA'
                                    'XEAAAAAAAABAAAAAWIAAAAAAAAAAAAAAUHT/KYA'
                                    'AABAXjLTCpiQPI7fr0svzAGpe/lFscc/PDTYvLU'
                                    'V2CxjFodWa2vPOKGfMy1MdhhpP8grn3VfjcSWaZ7UU50XdKlVCA=='}

    raw_tx = RawTransaction(horizon_resp)
    with pytest.raises(CantSimplifyError, match='Cant simplify operation of type ManageData'):
        SimplifiedTransaction(raw_tx)


def test_cant_simplify_memo():
    horizon_resp = {'envelope_xdr': 'AAAAACkAOLSo0e7OrmwNrBEiHlFVayj648y6XKCwE'
                                    'AxrRtVRAAAAZAAKySEAAAADAAAAAQAAAAAAAAAAAA'
                                    'AAAAAAAAAAAAAAAAAAAQAAAAAAAAAKAAAAAXEAAAA'
                                    'AAAABAAAAAWIAAAAAAAAAAAAAAUHT/KYAAABAXjLT'
                                    'CpiQPI7fr0svzAGpe/lFscc/PDTYvLUV2CxjFodWa'
                                    '2vPOKGfMy1MdhhpP8grn3VfjcSWaZ7UU50XdKlVCA=='}

    raw_tx = RawTransaction(horizon_resp)
    with pytest.raises(CantSimplifyError, match='Cant simplify tx with memo type: IdMemo'):
        SimplifiedTransaction(raw_tx)


def test_cant_simplify_op_count():
    horizon_resp = {'envelope_xdr': 'AAAAACkAOLSo0e7OrmwNrBEiHlFVayj648y6XKCwEAx'
                                    'rRtVRAAAAyAAKySEAAAADAAAAAQAAAAAAAAAAAAAAAAA'
                                    'AAAAAAAAAAAAAAgAAAAAAAAABAAAAACkAOLSo0e7Ormw'
                                    'NrBEiHlFVayj648y6XKCwEAxrRtVRAAAAAAAAAAAAAYag'
                                    'AAAAAAAAAAEAAAAAKQA4tKjR7s6ubA2sESIeUVVrKPrjz'
                                    'LpcoLAQDGtG1VEAAAAAAAAAAAABhqAAAAAAAAAAAUHT/KY'
                                    'AAABA7G1OveovPOUBxJjFDL18tnyueSlFhZesHexghyUxSy'
                                    'LQmWtQm04uOGBHOgX3d9nyL7OAkJM9a7y7FCMnJy7ACg=='}

    raw_tx = RawTransaction(horizon_resp)
    with pytest.raises(CantSimplifyError, match='Cant simplify tx with 2 operations'):
        SimplifiedTransaction(raw_tx)


def test_cant_simplify_asset():
    horizon_resp = {'envelope_xdr': 'AAAAACkAOLSo0e7OrmwNrBEiHlFVayj648y6XKCwEAxrRtVRAA'
                                    'AAZAAKySEAAAADAAAAAAAAAAAAAAABAAAAAAAAAAEAAAAAKQA4t'
                                    'KjR7s6ubA2sESIeUVVrKPrjzLpcoLAQDGtG1VEAAAABUk9OAAAAA'
                                    'AApADi0qNHuzq5sDawRIh5RVWso+uPMulygsBAMa0bVUQAAAAAAm'
                                    'JaAAAAAAAAAAAFB0/ymAAAAQLeBV/mb2aRGjq1VmCHtcA9FCadQg'
                                    'ySl4QUesiAUuebSIQNTghNWSepyb0OkFfXjkn9gHl9ckPhZ1lnpoWvZwQU='}

    raw_tx = RawTransaction(horizon_resp)
    with pytest.raises(CantSimplifyError, match='Cant simplify operation with asset RON issued by '
                                                'GAUQAOFUVDI65TVONQG2YEJCDZIVK2ZI7LR4ZOS4UCYBADDLI3KVCKSX'):
        SimplifiedTransaction(raw_tx)
