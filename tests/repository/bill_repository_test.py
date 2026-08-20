"""Tests for the BillRepository Class"""

from datetime import datetime, timedelta
from decimal import Decimal

from sqlmodel import select
from billflux.infra.config.database import get_session
from billflux.infra.entities.bill import Bill


def test_insert_bill(bill_repository):
    """
    Testando o metodo insert_bill
    """

    now = datetime.now()
    response = bill_repository.insert_bill(
        status=False,
        due_date=now,
        value=Decimal("123.45"),
        reference="Energia",
        suplyer="CEMIG",
        bill_type="Boleto",
        days=5,
        payday=None,
        value_from_payment=None,
        bar_code="12345",
        pix_key="key",
        pix_payload="payload",
        pix_image="img",
        obs="obs",
        date_from_add=now,
    )

    with get_session() as session:
        query_user = session.exec(select(Bill).where(Bill.bar_code == "12345")).one()

    # Testing if the information sent by the metod is in database.
    assert response.bar_code == query_user.bar_code
    assert response.bill_type == query_user.bill_type
    assert response.suplyer == query_user.suplyer
    assert response.pix_key == query_user.pix_key
    assert response.pix_payload == query_user.pix_payload
    assert response.pix_image == query_user.pix_image


def test_cleanup_pix_data_removes_paid_expired_only(bill_repository):
    """Only PIX image/payload of paid bills past retention are cleared."""

    repo = bill_repository
    old_paid = repo.insert_bill(
        value=10,
        due_date=datetime(2026, 1, 1),
        bar_code="111",
        status=True,
        payday=datetime.now() - timedelta(days=30),
        pix_image="img1",
        pix_payload="p1",
    )
    recent_paid = repo.insert_bill(
        value=20,
        due_date=datetime(2026, 1, 1),
        bar_code="222",
        status=True,
        payday=datetime.now() - timedelta(days=1),
        pix_image="img2",
        pix_payload="p2",
    )
    unpaid = repo.insert_bill(
        value=30,
        due_date=datetime(2026, 1, 1),
        bar_code="333",
        status=False,
        payday=None,
        pix_image="img3",
        pix_payload="p3",
    )

    removed = repo.cleanup_pix_data(days=7)

    assert removed >= 1
    assert repo.get_bill(old_paid.id).pix_image is None
    assert repo.get_bill(old_paid.id).pix_payload is None
    assert repo.get_bill(recent_paid.id).pix_image == "img2"
    assert repo.get_bill(unpaid.id).pix_image == "img3"
