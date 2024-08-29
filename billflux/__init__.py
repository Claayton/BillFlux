"""Module to create the app"""

import os
from flask import Flask
from dynaconf import FlaskDynaconf
from dotenv import load_dotenv
from billflux.controlers import home, bills, insert_bill
from billflux.infra.config.database import create_db


def create_app():
    """Function that creates the app"""

    load_dotenv()
    create_db()

    app = Flask(__name__)

    FlaskDynaconf(
        app, environments=True, envvar_prefix="FLASK", settings_files=["settings.toml"]
    )

    app.register_blueprint(home.bp)
    app.register_blueprint(bills.bp)
    app.register_blueprint(insert_bill.bp)

    return app
