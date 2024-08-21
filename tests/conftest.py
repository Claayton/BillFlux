"""Conftest for tests"""

from pytest import fixture
from billflux import create_app
from tests.mocks.mock_bills import mock_bill


@fixture(scope="module")
def app():
    """Configura o aplicativo de teste com um banco de dados em memória."""
    return create_app()


ticket = mock_bill()


@fixture(scope="module")
def fake_bill():
    """Mock de usuario"""

    return ticket
