"""Conftest for tests"""

from pytest import fixture
from tests.mocks.mock_bills import mock_bill

ticket = mock_bill()


@fixture(scope="module")
def fake_bill():
    """Mock de usuario"""

    return ticket
