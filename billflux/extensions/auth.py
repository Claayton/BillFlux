"""Init the login manager extension"""

from flask_login import LoginManager

lm = LoginManager()


def init_app(app):
    """Init the login manager extension"""
    lm.init_app(app)
    lm.login_view = "login"
    return app
