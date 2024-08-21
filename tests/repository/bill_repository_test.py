"""Tests for the BillRepository Class"""

from billflux.infra.repository.bill_repository import BillRepository
from billflux.infra.config.database import get_session
from billflux.infra.entities.models import Bill
from sqlmodel import select


def test_insert_Bill(fake_bill, bill_repository):
    """
    Testando o metodo insert_bill()
    """

    response = bill_repository.insert_bill(
        bar_code=fake_bill.bar_code,
        type=fake_bill.type,
        suplyer=fake_bill.suplyer,
    )

    with get_session() as session:
        query_user = session.exec(
            select(Bill).where(Bill.bar_code == fake_bill.bar_code)
        ).one()

    # Testando se as informacoes enviadas pelo metodo estao no db.
    assert response.bar_code == query_user.bar_code
    assert response.type == query_user.type
    assert response.suplyer == query_user.suplyer
