"""Module to create the app"""

from flask import Flask
from dynaconf import FlaskDynaconf
from flask_wtf import CSRFProtect
from billflux.config import settings
from billflux.infra.config.database import create_db
from billflux.controlers import home, bills, insert_bill, auth, accounts

csrf = CSRFProtect()


def _seed_default_user():
    """Creates the default user from settings.toml if it does not exist."""
    from billflux.infra.repository.user_repository import UserRepository

    username = getattr(settings.auth, "username", None)
    password_hash = getattr(settings.auth, "password_hash", None)

    if not username or not password_hash:
        return

    repository = UserRepository()
    if repository.get_user_by_username(username) is None:
        repository.create_user(username=username, password_hash=password_hash)


def _seed_default_accounts():
    """Cria categorias padrão no plano de contas se a tabela estiver vazia."""
    from billflux.infra.repository.account_repository import AccountRepository

    repository = AccountRepository()
    if repository.get_accounts():
        return

    for name in ("Vendas", "Outras receitas"):
        repository.insert_account(name=name, type="receita")
    for name in (
        "Compras / Mercadorias",
        "Aluguel",
        "Água e Luz",
        "Internet",
        "Funcionários",
        "Impostos",
        "Outras despesas",
    ):
        repository.insert_account(name=name, type="despesa")


def create_app():
    """Function that creates the app"""

    app = Flask(__name__)
    FlaskDynaconf(app, dynaconf_instance=settings)
    app.secret_key = settings.secret_key
    csrf.init_app(app)
    create_db()
    _seed_default_user()
    _seed_default_accounts()
    app.register_blueprint(home.bp)
    app.register_blueprint(bills.bp)
    app.register_blueprint(insert_bill.bp)
    app.register_blueprint(auth.bp)
    app.register_blueprint(accounts.bp)
    return app
