"""Module for database configuration and creation"""

from sqlmodel import create_engine, Session
from billflux.config import settings
from billflux.infra.entities.models import *  # noqa: F405


engine = create_engine(settings.database.url)


def create_db():
    """Criando bancos de dados"""

    base = SQLModel.metadata.create_all(engine)

    return base


def get_session():
    return Session(engine)
