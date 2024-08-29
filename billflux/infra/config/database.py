"""Module for database configuration and creation"""

# flake8: noqa: F405

import os
from sqlmodel import create_engine, Session
from billflux.config import settings
from billflux.infra.entities.bill import *  # pylint: disable=W0401, W0614


def create_db():
    """Creating databases"""

    database_url_development = settings["development"].DATABASE_URL
    database_url_testing = settings["testing"].DATABASE_URL

    if not os.path.exists(database_url_development.replace("sqlite:///", "")):

        print("Development database not found!, creating!")
        engine = create_engine(database_url_development)
        SQLModel.metadata.create_all(engine)

    else:
        print("Database found!")

    if not os.path.exists(database_url_testing.replace("sqlite:///", "")):

        print("Testing database not found!, creating!")
        engine = create_engine(database_url_testing)
        SQLModel.metadata.create_all(engine)

    else:
        print("Database found!")

    return print("All good!")


def get_session(engine):
    """GetSession from database function"""
    return Session(engine)
