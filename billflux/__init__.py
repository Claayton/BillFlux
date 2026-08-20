"""Module to create the app"""

from flask import Flask
from dynaconf import FlaskDynaconf
from flask_wtf import CSRFProtect
from billflux.config import settings
from billflux.infra.config.database import create_db
from billflux.api import bp as api_bp
from billflux.api import auth as api_auth
from billflux.api import dashboard as api_dashboard
from billflux.api import sales as api_sales
from billflux.api import bills as api_bills
from billflux.api import products as api_products
from billflux.api import accounts as api_accounts
from billflux.api import payments as api_payments
from billflux.api import pdv as api_pdv

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


def _seed_default_payment_methods():
    """Cria as formas de pagamento padrão se a tabela estiver vazia."""
    from billflux.infra.repository.payment_method_repository import (
        PaymentMethodRepository,
    )

    repository = PaymentMethodRepository()
    if repository.get_methods():
        return

    for name in ("Dinheiro", "PIX", "Crédito", "Débito", "VR/VA"):
        repository.insert_method(name=name)


def create_app():
    """Function that creates the app"""

    app = Flask(__name__)
    FlaskDynaconf(app, dynaconf_instance=settings)
    app.secret_key = settings.secret_key
    csrf.init_app(app)
    create_db()
    _seed_default_user()
    _seed_default_accounts()
    _seed_default_payment_methods()

    app.register_blueprint(api_bp)

    @app.route("/", defaults={"path": ""})
    @app.route("/<path:path>")
    def spa_app(path):
        """Entrega o SPA (build do Vite) para qualquer rota não-reservada."""
        from flask import abort, send_from_directory

        if path.startswith(("api/", "static/")):
            return abort(404)
        return send_from_directory(app.static_folder, "app/index.html")

    return app
