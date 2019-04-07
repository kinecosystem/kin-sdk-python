import pytest

@pytest.mark.skip(reason='Blockchain sometimes returns 404, known broken')
def test_single_monitor(test_client, test_account):
    pass


@pytest.mark.skip(reason='Blockchain sometimes returns 404, known broken')
def test_multi_monitor(test_client, test_account):
    pass
