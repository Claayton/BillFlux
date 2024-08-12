from flask import Flask
from ticketmanager.controlers import home


def create_app():

    app = Flask(__name__)
    app.register_blueprint(home.bp)

    return app
