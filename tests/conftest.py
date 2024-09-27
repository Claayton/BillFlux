"""Conftest for tests"""

from pytest import fixture
from dynaconf import settings
from billflux import create_app
from tests.mocks import mock_user, mock_bill


@fixture(scope="module")
def app():
    """Configura o aplicativo de teste com um banco de dados em memória."""

    settings.configure(FORCE_ENV_FOR_DYNACONF="testing")

    yield create_app()


user = mock_user()
bill = mock_bill()


@fixture(scope="module")
def fake_user():
    """Mock of user"""

    return user


@fixture(scope="module")
def fake_bill():
    """Mock of bill"""

    return bill
