"""Module to create the app"""

from flask import Flask
from dynaconf import FlaskDynaconf
from billflux.controlers import home, bills


def create_app():
    """Function that creates the app"""

    app = Flask(__name__)
    FlaskDynaconf(app)
    app.register_blueprint(home.bp)
    app.register_blueprint(bills.bp)
    return app
