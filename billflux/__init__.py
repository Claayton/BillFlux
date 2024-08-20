from flask import Flask
from billflux.controlers import home, tickets


def create_app():

    app = Flask(__name__)
    app.register_blueprint(home.bp)
    app.register_blueprint(tickets.bp)

    return app
