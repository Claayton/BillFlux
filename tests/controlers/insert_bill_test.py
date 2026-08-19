"""Tests from insert_bill route"""

import re
from datetime import datetime
from decimal import Decimal

from billflux.infra.repository.bill_repository import BillRepository

BB_OLD_DATE_CODE = "00190000090334981726602168356174315130000038179"


def _get_csrf_token(client):
    """Fetch the CSRF token from the bills page form."""
    response = client.get("/bills/")
    match = re.search(
        r'name="csrf_token" value="([^"]+)"', response.get_data(as_text=True)
    )
    assert match, "CSRF token not found in /bills/ page"
    return match.group(1)


def test_insert_bill_valid(logged_client):
    """POSTing valid data should redirect and persist the bill"""

    response = logged_client.post(
        "/insert_bill/",
        data={
            "csrf_token": _get_csrf_token(logged_client),
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
    assert any(bill.bar_code == "1234567890" for bill in bills)


def test_insert_bill_missing_required(logged_client):
    """POSTing without required fields should redirect back to bills"""

    response = logged_client.post(
        "/insert_bill/",
        data={
            "csrf_token": _get_csrf_token(logged_client),
            "bar_code": "999",
            "value": "",
            "vencimento": "",
        },
    )

    assert response.status_code == 302


def test_insert_bill_without_csrf_token(logged_client):
    """POSTing without a CSRF token should be rejected"""

    response = logged_client.post(
        "/insert_bill/",
        data={"bar_code": "888", "value": "10,00", "vencimento": "2026-09-01"},
    )

    assert response.status_code == 400


def test_insert_bill_get_method(logged_client):
    """GET on insert_bill route should not be allowed"""

    response = logged_client.get("/insert_bill/")

    assert response.status_code == 405


def test_insert_bill_requires_login(client):
    """Unauthenticated POST should be redirected to login"""

    page = client.get("/login")
    token = re.search(
        r'name="csrf_token" value="([^"]+)"', page.get_data(as_text=True)
    ).group(1)

    response = client.post(
        "/insert_bill/",
        data={
            "csrf_token": token,
            "bar_code": "777",
            "value": "10,00",
            "vencimento": "2026-09-01",
        },
    )

    assert response.status_code == 302
    assert "/login" in response.headers["Location"]


def test_insert_bill_does_not_autofill_old_vencimento(logged_client):
    """A code with a stale factor must not autofill the due date."""

    response = logged_client.post(
        "/insert_bill/",
        data={
            "csrf_token": _get_csrf_token(logged_client),
            "bar_code": BB_OLD_DATE_CODE,
            "value": "",
            "vencimento": "",
        },
    )

    assert response.status_code == 302
    bills = BillRepository().get_bills()
    assert not any(bill.bar_code == BB_OLD_DATE_CODE for bill in bills)


def test_insert_bill_autofills_value_and_keeps_manual_vencimento(logged_client):
    """The value is autofilled but a manual due date is respected."""

    response = logged_client.post(
        "/insert_bill/",
        data={
            "csrf_token": _get_csrf_token(logged_client),
            "bar_code": BB_OLD_DATE_CODE,
            "value": "",
            "vencimento": "2026-07-20",
            "reference": "Teste vencimento",
            "suplyer": "Banco do Brasil",
            "bill_type": "Conta",
            "obs": "",
        },
        follow_redirects=True,
    )

    assert response.status_code == 200

    bill = next(
        (b for b in BillRepository().get_bills() if b.bar_code == BB_OLD_DATE_CODE),
        None,
    )
    assert bill is not None
    assert bill.value == Decimal("381.79")
    assert bill.due_date == datetime(2026, 7, 20)


def test_insert_bill_saves_pix_key(logged_client):
    """The optional PIX key field is persisted on insert."""
    bar_code = "00190000090334981726602168356174315130000038170"

    response = logged_client.post(
        "/insert_bill/",
        data={
            "csrf_token": _get_csrf_token(logged_client),
            "bar_code": bar_code,
            "value": "381,79",
            "vencimento": "2026-07-20",
            "reference": "Teste PIX",
            "suplyer": "Banco do Brasil",
            "bill_type": "Conta",
            "pix_key": "nubank@teste.com",
            "obs": "",
        },
        follow_redirects=True,
    )

    assert response.status_code == 200

    bill = next(
        (b for b in BillRepository().get_bills() if b.bar_code == bar_code),
        None,
    )
    assert bill is not None
    assert bill.pix_key == "nubank@teste.com"


def test_insert_bill_pix_key_optional(logged_client):
    """Inserting without a PIX key stores None, not an empty string."""
    bar_code = "00190000090334981726602168356174315130000038171"

    response = logged_client.post(
        "/insert_bill/",
        data={
            "csrf_token": _get_csrf_token(logged_client),
            "bar_code": bar_code,
            "value": "381,79",
            "vencimento": "2026-07-20",
            "reference": "Sem chave",
            "suplyer": "Banco do Brasil",
            "bill_type": "Conta",
            "pix_key": "",
            "obs": "",
        },
        follow_redirects=True,
    )

    assert response.status_code == 200

    bill = next(
        (b for b in BillRepository().get_bills() if b.bar_code == bar_code),
        None,
    )
    assert bill is not None
    assert bill.pix_key is None


def test_insert_bill_saves_pix_payload(logged_client):
    """A decoded PIX payload (from a QR image) is persisted on insert."""
    bar_code = "00190000090334981726602168356174315130000038172"
    payload = (
        "00020126410014br.gov.bcb.pix0119nubank@thalesog.com5204000053039865406"
        "381.795802BR5915BANCO DO BRASIL6008BRASILIA62070503***6304ABCD"
    )

    response = logged_client.post(
        "/insert_bill/",
        data={
            "csrf_token": _get_csrf_token(logged_client),
            "bar_code": bar_code,
            "value": "381,79",
            "vencimento": "2026-07-20",
            "reference": "QR por imagem",
            "suplyer": "Banco do Brasil",
            "bill_type": "Conta",
            "pix_key": "",
            "pix_payload": payload,
            "obs": "",
        },
        follow_redirects=True,
    )

    assert response.status_code == 200

    bill = next(
        (b for b in BillRepository().get_bills() if b.bar_code == bar_code),
        None,
    )
    assert bill is not None
    assert bill.pix_payload == payload


def test_insert_bill_saves_pix_image(logged_client):
    """The QR image (base64 fallback) is persisted on insert."""
    bar_code = "00190000090334981726602168356174315130000038173"
    image = "data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAAB"

    response = logged_client.post(
        "/insert_bill/",
        data={
            "csrf_token": _get_csrf_token(logged_client),
            "bar_code": bar_code,
            "value": "381,79",
            "vencimento": "2026-07-20",
            "reference": "QR por imagem",
            "suplyer": "Banco do Brasil",
            "bill_type": "Conta",
            "pix_key": "",
            "pix_payload": "",
            "pix_image": image,
            "obs": "",
        },
        follow_redirects=True,
    )

    assert response.status_code == 200

    bill = next(
        (b for b in BillRepository().get_bills() if b.bar_code == bar_code),
        None,
    )
    assert bill is not None
    assert bill.pix_image == image
