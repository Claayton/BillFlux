"""Test from delete_bill route"""

from unittest.mock import patch
from billflux.infra.entities.bills import Bill as BillModel
from billflux.infra.entities.users import User as UserModel


def test_delete_bill(client, fake_user, fake_bill, get_test_session):
    """Test to delete bill route"""

    url = f"/delete_bill/{fake_bill.id}"

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

        new_bill = BillModel(
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
            user_id=new_user.id,
        )

        session.add(new_user)
        session.add(new_bill)
        session.commit()

        with patch(
            "billflux.controlers.bills.delete_bill.database_url", "sqlite:///teste.db"
        ):

            response = client.delete(url)

            assert response.status_code == 204
