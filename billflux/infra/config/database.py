"""Module for database configuration and creation"""

# flake8: noqa: F405

from sqlalchemy import inspect, text
from sqlalchemy.pool import StaticPool
from sqlmodel import create_engine, Session
from billflux.config import settings
from billflux.infra.entities.bill import *  # pylint: disable=W0401, W0614
from billflux.infra.entities.account import Account  # noqa: F401

_database_url = settings.database.url
_engine_kwargs = {"connect_args": {"check_same_thread": False}}

if ":memory:" in _database_url or _database_url == "sqlite://":
    _engine_kwargs["poolclass"] = StaticPool

engine = create_engine(_database_url, **_engine_kwargs)


def _add_column_if_missing(table: str, column: str, column_type: str = "VARCHAR"):
    """Adds a column to an existing table without dropping data."""
    with engine.connect() as connection:
        existing = [col["name"] for col in inspect(connection).get_columns(table)]
        if column not in existing:
            connection.execute(
                text(f"ALTER TABLE {table} ADD COLUMN {column} {column_type}")
            )
            connection.commit()


def create_db():
    """Criando bancos de dados"""

    base = SQLModel.metadata.create_all(engine)
    _add_column_if_missing("bill", "pix_key")
    _add_column_if_missing("bill", "pix_payload")
    _add_column_if_missing("bill", "pix_image")
    _add_column_if_missing("bill", "account_id", "INTEGER")

    return base


def get_session():
    """GetSession from database function"""
    return Session(engine)
