from flask import Flask
from billflux.config import settings
from .home import bp as home_bp


def create_app():
    app = Flask(__name__)
    
    # Configurando uma chave secreta
    app.secret_key = settings.SECRET_KEY
    
    # Registra o blueprint
    app.register_blueprint(home_bp)

    return app
