"""Module for database configuration and creation"""

# flake8: noqa: F405

from sqlmodel import create_engine, Session
from billflux.config import settings
from billflux.infra.entities.bill import *  # pylint: disable=W0401, W0614


def create_db():
    """Criando bancos de dados"""

    engine = create_engine(settings["development"].DATABASE_URL)
    base = SQLModel.metadata.create_all(engine)

    return base


def get_session(engine):
    """GetSession from database function"""
    return Session(engine)
