"""Tests for the BillRepository Class"""

from sqlmodel import select
from billflux.infra.config.database import get_session
from billflux.infra.entities.bill import Bill


def test_insert_bill(fake_bill, bill_repository):
    """
    Testando o metodo insert_bill
    """

    response = bill_repository.insert_bill(
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

    with get_session() as session:
        query_user = session.exec(
            select(Bill).where(Bill.bar_code == fake_bill.bar_code)
        ).one()

    # Testing if the information sent by the metod is in database.
    assert response.bar_code == query_user.bar_code
    assert response.bill_type == query_user.bill_type
    assert response.suplyer == query_user.suplyer
