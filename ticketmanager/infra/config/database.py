from sqlmodel import create_engine, Session
from ticketmanager.config import settings
from ticketmanager.infra.entities.models import *


engine = create_engine(settings.database.url)


def create_db():
    """Criando bancos de dados"""

    base = SQLModel.metadata.create_all(engine)

    return base


def get_session():
    return Session(engine)
