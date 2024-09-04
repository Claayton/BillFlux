from flask import Flask

def create_app():
    app = Flask(__name__)
    
    # Importa o blueprint
    from .home import bp as home_bp
    # Registra o blueprint
    app.register_blueprint(home_bp)

    return app
