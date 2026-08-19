"""Module to create the app"""

from flask import Flask
from dynaconf import FlaskDynaconf
from flask_wtf import CSRFProtect
from billflux.config import settings
from billflux.infra.config.database import create_db
from billflux.controlers import home, bills, insert_bill, auth

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


def create_app():
    """Function that creates the app"""

    app = Flask(__name__)
    FlaskDynaconf(app, dynaconf_instance=settings)
    app.secret_key = settings.secret_key
    csrf.init_app(app)
    create_db()
    _seed_default_user()
    app.register_blueprint(home.bp)
    app.register_blueprint(bills.bp)
    app.register_blueprint(insert_bill.bp)
    app.register_blueprint(auth.bp)
    return app
