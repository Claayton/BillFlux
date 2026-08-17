"""Tests from insert_bill route"""

import re

from billflux.infra.repository.bill_repository import BillRepository


def _get_csrf_token(client):
    """Fetch the CSRF token from the bills page form."""
    response = client.get("/bills/")
    match = re.search(
        r'name="csrf_token" value="([^"]+)"', response.get_data(as_text=True)
    )
    assert match, "CSRF token not found in /bills/ page"
    return match.group(1)


def test_insert_bill_valid(client):
    """POSTing valid data should redirect and persist the bill"""

    response = client.post(
        "/insert_bill/",
        data={
            "csrf_token": _get_csrf_token(client),
            "bar_code": "1234567890",
            "value": "150,50",
            "vencimento": "2026-09-01",
            "reference": "Energia",
            "suplyer": "CEMIG",
            "bill_type": "Conta",
            "obs": "",
        },
        follow_redirects=True,
    )

    assert response.status_code == 200

    bills = BillRepository().get_bills()
    assert any(bill.bar_code == 1234567890 for bill in bills)


def test_insert_bill_missing_required(client):
    """POSTing without required fields should redirect back to bills"""

    response = client.post(
        "/insert_bill/",
        data={
            "csrf_token": _get_csrf_token(client),
            "bar_code": "999",
            "value": "",
            "vencimento": "",
        },
    )

    assert response.status_code == 302


def test_insert_bill_without_csrf_token(client):
    """POSTing without a CSRF token should be rejected"""

    response = client.post(
        "/insert_bill/",
        data={"bar_code": "888", "value": "10,00", "vencimento": "2026-09-01"},
    )

    assert response.status_code == 400


def test_insert_bill_get_method(client):
    """GET on insert_bill route should not be allowed"""

    response = client.get("/insert_bill/")

    assert response.status_code == 405
