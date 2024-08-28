"""Module for database configuration and creation"""

# flake8: noqa: F405

from sqlmodel import create_engine, Session
from dynaconf import settings
from billflux.infra.entities.bill import *  # pylint: disable=W0401, W0614

engine = create_engine(settings.DATABASE_URL)


def create_db():
    """Criando bancos de dados"""

    base = SQLModel.metadata.create_all(engine)

    return base


def get_session():
    """GetSession from database function"""
    return Session(engine)
