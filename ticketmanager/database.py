from sqlmodel import create_engine
from ticketmanager.config import settings
from ticketmanager.models import *


engine = create_engine(settings.database.url)


def create_db():
    """Criando bancos de dados"""

    base = SQLModel.metadata.create_all(engine)

    return base
