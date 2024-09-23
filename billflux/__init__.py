"""Module to create the app"""

import os
from flask import Flask
from dynaconf import FlaskDynaconf
from dotenv import load_dotenv
from billflux.extensions import auth
from billflux.controlers.home import home  # pylint: disable=E0401, E0611
from billflux.controlers.bills import (
    get_bills,
    insert_bill,
    delete_bill,
)  # pylint: disable=E0401, E0611
from billflux.infra.config.database import create_db


def create_app():
    """Function that creates the app"""

    load_dotenv()
    create_db()

    app = Flask(__name__)

    FlaskDynaconf(
        app, environments=True, envvar_prefix="FLASK", settings_files=["settings.toml"]
    )

    auth.init_app(app)

    app.register_blueprint(home.bp)
    app.register_blueprint(get_bills.bp)
    app.register_blueprint(insert_bill.bp)
    app.register_blueprint(delete_bill.bp)

    return app
