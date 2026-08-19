"""Tests from bills actions routes (pay, edit, delete)"""

import re
from datetime import datetime
from decimal import Decimal

from billflux.infra.repository.bill_repository import BillRepository


def _get_csrf_token(client):
    """Fetch the CSRF token from the bills page form."""
    response = client.get("/bills/")
    match = re.search(
        r'name="csrf_token" value="([^"]+)"', response.get_data(as_text=True)
    )
    assert match, "CSRF token not found in /bills/ page"
    return match.group(1)


def _insert_bill(bar_code="00000000000000000000000000000000000000000001"):
    """Creates a bill directly in the database and returns its id."""
    bill = BillRepository().insert_bill(
        value=Decimal("100.00"),
        due_date=datetime(2026, 9, 1),
        bar_code=bar_code,
        suplyer="CEMIG",
        bill_type="Conta",
    )
    return bill.id


def test_pay_bill(logged_client):
    """POSTing to pay should mark the bill as paid"""
    bill_id = _insert_bill()
    token = _get_csrf_token(logged_client)

    response = logged_client.post(
        f"/bills/pay/{bill_id}",
        headers={"X-CSRFToken": token},
        follow_redirects=True,
    )

    assert response.status_code == 200
    paid = BillRepository().get_bill(bill_id)
    assert paid.status is True
    assert paid.payday is not None


def test_pay_bill_not_found(logged_client):
    """Paying a non-existent bill should flash an error"""
    token = _get_csrf_token(logged_client)

    response = logged_client.post(
        "/bills/pay/999999",
        headers={"X-CSRFToken": token},
        follow_redirects=True,
    )

    assert response.status_code == 200
    assert "não encontrada" in response.get_data(as_text=True)


def test_edit_bill(logged_client):
    """POSTing to edit should update the bill fields"""
    bill_id = _insert_bill()
    token = _get_csrf_token(logged_client)

    response = logged_client.post(
        "/bills/edit",
        data={
            "csrf_token": token,
            "bill_id": str(bill_id),
            "bar_code": "00000000000000000000000000000000000000000009",
            "value": "250,75",
            "vencimento": "2026-10-15",
            "reference": "Energia de outubro",
            "suplyer": "COPEL",
            "bill_type": "Conta",
            "pix_key": "pix@copel.com.br",
            "obs": "atualizada",
        },
        follow_redirects=True,
    )

    assert response.status_code == 200
    updated = BillRepository().get_bill(bill_id)
    assert updated.value == Decimal("250.75")
    assert updated.suplyer == "COPEL"
    assert updated.reference == "Energia de outubro"
    assert updated.pix_key == "pix@copel.com.br"
    assert updated.obs == "atualizada"
    assert updated.bar_code == "00000000000000000000000000000000000000000009"


def test_edit_bill_missing_required(logged_client):
    """Editing without value/vencimento should not update"""
    bill_id = _insert_bill()
    token = _get_csrf_token(logged_client)

    response = logged_client.post(
        "/bills/edit",
        data={
            "csrf_token": token,
            "bill_id": str(bill_id),
            "value": "",
            "vencimento": "",
        },
        follow_redirects=True,
    )

    assert response.status_code == 200
    unchanged = BillRepository().get_bill(bill_id)
    assert unchanged.value == Decimal("100.00")


def test_delete_bill(logged_client):
    """POSTing to delete should remove the bill"""
    bill_id = _insert_bill()
    token = _get_csrf_token(logged_client)

    response = logged_client.post(
        f"/bills/delete/{bill_id}",
        headers={"X-CSRFToken": token},
        follow_redirects=True,
    )

    assert response.status_code == 200
    assert BillRepository().get_bill(bill_id) is None


def test_actions_require_login(client):
    """Unauthenticated requests should be redirected to login"""
    page = client.get("/login")
    token = re.search(
        r'name="csrf_token" value="([^"]+)"', page.get_data(as_text=True)
    ).group(1)

    assert (
        client.post(
            "/bills/pay/1",
            data={"csrf_token": token},
        ).status_code
        == 302
    )
    assert (
        client.post(
            "/bills/delete/1",
            data={"csrf_token": token},
        ).status_code
        == 302
    )
    assert (
        client.post(
            "/bills/edit",
            data={"csrf_token": token, "value": "10,00", "vencimento": "2026-09-01"},
        ).status_code
        == 302
    )


def test_actions_require_csrf(logged_client):
    """POSTs without a CSRF token should be rejected"""
    bill_id = _insert_bill()
    assert logged_client.post(f"/bills/pay/{bill_id}").status_code == 400
    assert logged_client.post(f"/bills/delete/{bill_id}").status_code == 400
