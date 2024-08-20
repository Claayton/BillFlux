import pytest
from billflux import create_app
from billflux.infra.config.database import create_db


@pytest.fixture
def client():
    app = create_app()
    app.testing = True
    app.config["TESTING"] = True
    app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///:memory:"

    with app.app_context():
        create_db()  # Cria as tabelas no banco de dados em memória

    with app.test_client() as client:
        yield client
