"""Tests from the payment methods routes"""

import re
from decimal import Decimal

from billflux.infra.repository.order_repository import OrderRepository
from billflux.infra.repository.payment_method_repository import PaymentMethodRepository
from billflux.infra.repository.product_repository import ProductRepository


def _csrf(client):
    page = client.get("/payments")
    match = re.search(r'name="csrf_token" value="([^"]+)"', page.get_data(as_text=True))
    assert match, "CSRF token not found in /payments page"
    return match.group(1)


def test_payments_requires_login(client):
    """Unauthenticated users should be redirected to login."""

    response = client.get("/payments")

    assert response.status_code == 302
    assert "/login" in response.headers["Location"]


def test_payments_page_shows_seeded_methods(logged_client):
    """GET /payments should render the seeded payment methods."""

    response = logged_client.get("/payments")

    assert response.status_code == 200
    page = response.get_data(as_text=True)
    assert "Formas de pagamento" in page
    assert "Dinheiro" in page
    assert "PIX" in page


def test_create_method(logged_client):
    """POSTing a new method should persist it."""

    token = _csrf(logged_client)
    logged_client.post(
        "/payments/new",
        data={"csrf_token": token, "name": "Método do Teste"},
        follow_redirects=True,
    )

    names = [method.name for method in PaymentMethodRepository().get_methods()]
    assert "Método do Teste" in names


def test_toggle_method(logged_client):
    """Toggling a method should flip its active state."""

    method = PaymentMethodRepository().insert_method("Toggle Teste")
    token = _csrf(logged_client)

    logged_client.post(
        f"/payments/toggle/{method.id}",
        headers={"X-CSRFToken": token},
        follow_redirects=True,
    )

    assert PaymentMethodRepository().get_method(method.id).active is False


def test_delete_method_blocked_when_used(logged_client):
    """A method used in orders cannot be deleted."""

    method = PaymentMethodRepository().insert_method("Em Uso Teste")
    product = ProductRepository().insert_product(
        name="Pagamento Em Uso", price=Decimal("1.00"), stock_quantity=3
    )
    OrderRepository().create_order([(product.id, 1)], method.id)

    token = _csrf(logged_client)
    logged_client.post(
        f"/payments/delete/{method.id}",
        headers={"X-CSRFToken": token},
        follow_redirects=True,
    )

    assert PaymentMethodRepository().get_method(method.id) is not None
