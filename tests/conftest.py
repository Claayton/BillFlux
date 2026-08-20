"""Conftest for tests"""

import os

os.environ["BILLFLUX_DATABASE__URL"] = "sqlite://"

from pytest import fixture  # noqa: E402
from billflux import create_app  # noqa: E402


def login(client):
    """Autentica o client de teste via API com o usuário fixo do settings."""
    token = client.get("/api/auth/csrf").get_json()["csrf_token"]
    response = client.post(
        "/api/auth/login",
        json={"username": "admin", "password": "admin"},
        headers={"X-CSRFToken": token},
    )
    assert response.status_code == 200


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
