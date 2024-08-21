"""Module to create the app"""

from flask import Flask
from billflux.controlers import home, bills


def create_app():

    app = Flask(__name__)
    app.register_blueprint(home.bp)
    app.register_blueprint(bills.bp)

    return app
