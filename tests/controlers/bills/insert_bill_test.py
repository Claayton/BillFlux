"""Tests for insert_bill route"""

from unittest.mock import patch
from flask_login import login_user
from billflux.infra.entities.users import User as UserModel
from billflux.infra.entities.bills import Bill as BillModel


def test_insert_bill(client, fake_bill, fake_user, get_test_session, clean_database):
    """Test to insert a new bill route"""

    url = "/insert_bill/"
    data = {
        "bar_code": fake_bill.bar_code,
        "value": fake_bill.value,
        "vencimento": fake_bill.due_date.strftime("%Y-%m-%d"),
        "reference": fake_bill.reference,
        "suplyer": fake_bill.suplyer,
        "bill_type": fake_bill.bill_type,
        "obs": fake_bill.obs,
    }

    with get_test_session as session:

        new_user = UserModel(
            id=fake_user.id,
            name=fake_user.name,
            email=fake_user.email,
            password_hash=fake_user.password_hash,
            secundary_id=fake_user.secundary_id,
            is_staff=fake_user.is_staff,
            is_active_user=fake_user.is_active_user,
            date_joined=fake_user.date_joined,
            last_login=fake_user.last_login,
        )
        session.add(new_user)
        session.commit()

    user = UserModel(id=fake_user.id, email=fake_user.email)
    login_user(user)

    with patch(
        "billflux.controlers.bills.insert_bill.database_url", "sqlite:///teste.db"
    ):

        try:

            response = client.post(url, data=data)

            assert response.status_code == 302

        finally:
            clean_database  # pylint: disable=W0104
