"""Conftest for tests"""

import os

os.environ["BILLFLUX_DATABASE__URL"] = "sqlite://"

import re  # noqa: E402

from pytest import fixture  # noqa: E402
from billflux import create_app  # noqa: E402
from tests.mocks.mock_bills import mock_bill  # noqa: E402


def login(client):
    """Autentica o client de teste com o usuário fixo do settings."""
    page = client.get("/login")
    match = re.search(r'name="csrf_token" value="([^"]+)"', page.get_data(as_text=True))
    assert match, "CSRF token not found in /login page"
    response = client.post(
        "/login",
        data={"csrf_token": match.group(1), "username": "admin", "password": "admin"},
    )
    assert response.status_code == 302


@fixture(scope="module", autouse=True)
def create_database():
    """Garante que as tabelas existam no banco em memória."""
    from billflux.infra.config.database import create_db

    create_db()


@fixture(scope="module")
def app():
    """Configura o aplicativo de teste com um banco de dados em memória."""
    return create_app()


@fixture
def logged_client(client):
    """Client de teste já autenticado."""
    login(client)
    return client


ticket = mock_bill()


@fixture(scope="module")
def fake_bill():
    """Mock de usuario"""

    return ticket
