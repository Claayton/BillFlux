"""Tests for the BillRepository Class"""

from sqlmodel import select
from billflux.infra.entities.bill import Bill


def test_insert_bill(fake_bill, bill_repository, get_test_session):
    """
    Testing the insert_bill method.
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

    with get_test_session as session:
        query_bill = session.exec(
            select(Bill).where(Bill.bar_code == fake_bill.bar_code)
        ).one()

    # Testing if the information sent by the method is in database.
    assert response.bar_code == query_bill.bar_code
    assert response.bill_type == query_bill.bill_type
    assert response.suplyer == query_bill.suplyer


def test_delete_bill(fake_bill, bill_repository_with_one_bill, get_test_session):
    """Testing the delete_bill method"""

    with get_test_session as session:
        query_bill = session.exec(select(Bill).where(Bill.id == fake_bill.id)).one()

    response = bill_repository_with_one_bill.delete_bill(bill_id=fake_bill.id)

    # Testing if the information sent by the method is in database.
    assert response.bar_code == query_bill.bar_code
    assert response.bill_type == query_bill.bill_type
    assert response.suplyer == query_bill.suplyer
