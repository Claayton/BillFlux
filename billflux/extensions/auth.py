"""Init the login manager extension"""

from flask_login import LoginManager
from sqlmodel import create_engine, select
from billflux.infra.config.database import get_session
from billflux.config import settings
from billflux.infra.entities import User


lm = LoginManager()


def init_app(app):
    """Init the login manager extension"""
    lm.init_app(app)
    lm.login_view = "bp_home.login"

    return app


@lm.user_loader
def load_user(user_id):
    """Load one user"""

    database_url = settings["development"].DATABASE_URL
    engine = create_engine(database_url)

    with get_session(engine) as session:

        user = session.exec(select(User).where(User.id == user_id)).one_or_none()

    if user:
        print(f"Usuário carregado: {user.email}")
    else:
        print("Usuário não encontrado.")

    return user
