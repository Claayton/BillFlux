"""Conftest for tests"""

from pytest import fixture
from dynaconf import settings
from billflux import create_app
from sqlmodel import delete, create_engine
from billflux.config import settings as setting_db
from billflux.infra.config.database import get_session
from billflux.infra.entities.bills import Bill as BillModel
from billflux.infra.entities.users import User as UserModel
from tests.mocks import mock_user, mock_bill


@fixture(scope="module")
def app():
    """Configura o aplicativo de teste com um banco de dados em memória."""

    settings.configure(FORCE_ENV_FOR_DYNACONF="testing")

    yield create_app()


@fixture(scope="function")
def get_test_session():
    """Fixture to get a session test"""

    engine = create_engine(setting_db["testing"].DATABASE_URL)

    return get_session(engine)


@fixture(scope="function")
def clean_database(get_test_session):  # pylint: disable=w0621
    """Fixture to clean database"""

    with get_test_session as session:
        session.exec(delete(BillModel))
        session.exec(delete(UserModel))
        session.commit()


user = mock_user()
bill = mock_bill()


@fixture(scope="module")
def fake_user():
    """Mock of user"""

    return user


@fixture(scope="module")
def fake_bill():
    """Mock of bill"""

    return bill
