import pytest

import json
from kin.transactions import SimplifiedTransaction, RawTransaction
from kin.errors import CantSimplifyError


def test_success():
    horizon_resp = {'created_at': '',
                    'envelope_xdr': 'AAAAACkAOLSo0e7OrmwNrBEiHlFVayj648y6XKCwE'
                                    'AxrRtVRAAAAZAAKySEAAAACAAAAAAAAAAEAAAAHMS'
                                    '1wMzY1LQAAAAABAAAAAQAAAABZg0A36c/vVaXtIHL'
                                    'OVKKAOziSFWIDM70wzmS0plBHqQAAAAAAAAAAZ4Dx'
                                    'TkLiA5bx7NU4iIPlrU3eTJI2uFTqzwBDpvlSL0QAA'
                                    'AAAAAAAAAAAAAAAAAACa0bVUQAAAEALIlA0XpHSID'
                                    'Qg1af6WKWyd5pseIKzJMtUlzzJuZ4Gduf14J7Uyh2'
                                    'rcOhsf8xJ9P1+p2wPET7sBPjcynNr44IPplBHqQAA'
                                    'AECZGfeLP6rHRqWmiRy02qdM8ZKgl5rgSto3eHGqx'
                                    'A9rEu3oEtw8lliprpjlornrDQ6lFbJ1wNdV7H5pEZy6laMK'}

    tx = SimplifiedTransaction(RawTransaction(horizon_resp))
    assert tx
    # Content of the tx already checked in test_client.test_get_transaction_data


def test_cant_simplify_type():
    horizon_resp = {'created_at': '',
                    'envelope_xdr': 'AAAAACkAOLSo0e7OrmwNrBEiHlFVayj648y6XKC'
                                    'wEAxrRtVRAAAAZAAKySEAAAADAAAAAQAAAAAAAA'
                                    'AAAAAAAAAAAAAAAAAAAAAAAQAAAAAAAAAKAAAAA'
                                    'XEAAAAAAAABAAAAAWIAAAAAAAAAAAAAAUHT/KYA'
                                    'AABAXjLTCpiQPI7fr0svzAGpe/lFscc/PDTYvLU'
                                    'V2CxjFodWa2vPOKGfMy1MdhhpP8grn3VfjcSWaZ7UU50XdKlVCA=='}

    raw_tx = RawTransaction(horizon_resp)
    with pytest.raises(CantSimplifyError, match='Cant simplify operation of type ManageData'):
        SimplifiedTransaction(raw_tx)


def test_cant_simplify_memo():
    horizon_resp = {'created_at': '',
                    'envelope_xdr': 'AAAAACkAOLSo0e7OrmwNrBEiHlFVayj648y6XKCwE'
                                    'AxrRtVRAAAAZAAKySEAAAADAAAAAQAAAAAAAAAAAA'
                                    'AAAAAAAAAAAAAAAAAAAQAAAAAAAAAKAAAAAXEAAAA'
                                    'AAAABAAAAAWIAAAAAAAAAAAAAAUHT/KYAAABAXjLT'
                                    'CpiQPI7fr0svzAGpe/lFscc/PDTYvLUV2CxjFodWa'
                                    '2vPOKGfMy1MdhhpP8grn3VfjcSWaZ7UU50XdKlVCA=='}

    raw_tx = RawTransaction(horizon_resp)
    with pytest.raises(CantSimplifyError, match='Cant simplify tx with memo type: IdMemo'):
        SimplifiedTransaction(raw_tx)


def test_cant_simplify_op_count():
    horizon_resp = {'created_at': '',
                    'envelope_xdr': 'AAAAACkAOLSo0e7OrmwNrBEiHlFVayj648y6XKCwEAx'
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
    horizon_resp = {'created_at': '',
                    'envelope_xdr': 'AAAAACkAOLSo0e7OrmwNrBEiHlFVayj648y6XKCwEAxrRtVRAA'
                                    'AAZAAKySEAAAADAAAAAAAAAAAAAAABAAAAAAAAAAEAAAAAKQA4t'
                                    'KjR7s6ubA2sESIeUVVrKPrjzLpcoLAQDGtG1VEAAAABUk9OAAAAA'
                                    'AApADi0qNHuzq5sDawRIh5RVWso+uPMulygsBAMa0bVUQAAAAAAm'
                                    'JaAAAAAAAAAAAFB0/ymAAAAQLeBV/mb2aRGjq1VmCHtcA9FCadQg'
                                    'ySl4QUesiAUuebSIQNTghNWSepyb0OkFfXjkn9gHl9ckPhZ1lnpoWvZwQU='}

    raw_tx = RawTransaction(horizon_resp)
    with pytest.raises(CantSimplifyError, match='Cant simplify operation with asset RON issued by '
                                                'GAUQAOFUVDI65TVONQG2YEJCDZIVK2ZI7LR4ZOS4UCYBADDLI3KVCKSX'):
        SimplifiedTransaction(raw_tx)
