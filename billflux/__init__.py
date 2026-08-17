"""Module to create the app"""

from flask import Flask
from dynaconf import FlaskDynaconf
from flask_wtf import CSRFProtect
from billflux.config import settings
from billflux.infra.config.database import create_db
from billflux.controlers import home, bills, insert_bill

csrf = CSRFProtect()


def create_app():
    """Function that creates the app"""

    app = Flask(__name__)
    FlaskDynaconf(app, dynaconf_instance=settings)
    app.secret_key = settings.secret_key
    csrf.init_app(app)
    create_db()
    app.register_blueprint(home.bp)
    app.register_blueprint(bills.bp)
    app.register_blueprint(insert_bill.bp)
    return app
