"""Conftest for tests/repository"""

from pytest import fixture
from sqlmodel import delete, create_engine
from billflux.infra.repository.bills_repository import BillRepository
from billflux.infra.entities.bills import Bill as BillModel
from billflux.infra.config.database import get_session
from billflux.config import settings


@fixture(scope="function")
def get_test_session():
    """Fixture to get a session test"""

    engine = create_engine(settings["testing"].DATABASE_URL)

    return get_session(engine)


@fixture(scope="function")
def clean_database(get_test_session):
    """Fixture to clean database"""

    with get_test_session as session:
        session.exec(delete(BillModel))
        session.commit()


@fixture(scope="function")
def bill_repository(clean_database):  # pylint: disable=W0621
    """Fixture para montar o objeto UserRepository"""

    try:
        yield BillRepository(database_url=settings["testing"].DATABASE_URL)

    finally:
        clean_database


@fixture(scope="function")
def bill_repository_with_one_bill(
    bill_repository, fake_bill, get_test_session, clean_database
):  # pylint: disable=W0621
    """Fixture to show a object UserRepository whit one bill added."""

    with get_test_session as session:

        bill = BillModel(
            id=fake_bill.id,
            status=fake_bill.status,
            due_date=fake_bill.due_date,
            value=fake_bill.value,
            reference=fake_bill.reference,
            suplyer=fake_bill.suplyer,
            bill_type=fake_bill.bill_type,
            days=fake_bill.days,
            payday=fake_bill.payday,
            value_from_payment=fake_bill.value_from_payment,
            bar_code=fake_bill.bar_code,
            obs=fake_bill.obs,
            date_from_add=fake_bill.date_from_add,
            user_id=fake_bill.user_id,
        )

        session.add(bill)
        session.commit()

        try:
            yield bill_repository
        finally:
            clean_database
