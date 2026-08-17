"""Conftest for tests"""

import os

os.environ["BILLFLUX_DATABASE__URL"] = "sqlite://"

from pytest import fixture  # noqa: E402
from billflux import create_app  # noqa: E402
from tests.mocks.mock_bills import mock_bill  # noqa: E402


@fixture(scope="module", autouse=True)
def create_database():
    """Garante que as tabelas existam no banco em memória."""
    from billflux.infra.config.database import create_db

    create_db()


@fixture(scope="module")
def app():
    """Configura o aplicativo de teste com um banco de dados em memória."""
    return create_app()


ticket = mock_bill()


@fixture(scope="module")
def fake_bill():
    """Mock de usuario"""

    return ticket
