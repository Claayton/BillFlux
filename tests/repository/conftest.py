"""Conftest for tests/repository"""

from pytest import fixture
from sqlmodel import delete
from billflux.infra.repository.bill_repository import BillRepository
from billflux.infra.entities.bill import Bill as BillModel
from billflux.infra.config.database import get_session


@fixture(scope="function")
def bill_repository():
    """Fixture para montar o objeto UserRepository"""

    with get_session() as session:

        with session.begin():
            yield BillRepository()


@fixture(scope="function")
def bill_repository_with_one_bill(bill_repository, fake_bill):  # pylint: disable=W0621
    """Fixture to show a object UserRepository whit one bill added."""

    with get_session() as session:

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
        )

        session.add(bill)
        session.commit()

        try:
            yield bill_repository
        finally:
            try:
                # Limpar dados das tabelas
                session.exec(delete(BillModel))
                session.commit()
            except Exception as e:
                session.rollback()
                raise e
