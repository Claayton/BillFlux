from pytest import fixture
from tests.mocks.mock_tickets import mock_ticket

ticket = mock_ticket()


@fixture(scope="module")
def fake_ticket():
    """Mock de usuario"""

    return ticket
