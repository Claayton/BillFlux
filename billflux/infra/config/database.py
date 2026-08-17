"""Module for database configuration and creation"""

# flake8: noqa: F405

from sqlalchemy.pool import StaticPool
from sqlmodel import create_engine, Session
from billflux.config import settings
from billflux.infra.entities.bill import *  # pylint: disable=W0401, W0614

_database_url = settings.database.url
_engine_kwargs = {"connect_args": {"check_same_thread": False}}

if ":memory:" in _database_url or _database_url == "sqlite://":
    _engine_kwargs["poolclass"] = StaticPool

engine = create_engine(_database_url, **_engine_kwargs)


def create_db():
    """Criando bancos de dados"""

    base = SQLModel.metadata.create_all(engine)

    return base


def get_session():
    """GetSession from database function"""
    return Session(engine)
