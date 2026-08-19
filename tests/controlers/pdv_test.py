"""Tests from the PDV routes"""

import re
from decimal import Decimal

from billflux.infra.repository.order_repository import OrderRepository
from billflux.infra.repository.payment_method_repository import PaymentMethodRepository
from billflux.infra.repository.product_repository import ProductRepository


def _csrf(client):
    page = client.get("/pdv")
    match = re.search(r'name="csrf_token" value="([^"]+)"', page.get_data(as_text=True))
    assert match, "CSRF token not found in /pdv page"
    return match.group(1)


def test_pdv_requires_login(client):
    """Unauthenticated users should be redirected to login."""

    response = client.get("/pdv")

    assert response.status_code == 302
    assert "/login" in response.headers["Location"]


def test_pdv_page(logged_client):
    """GET /pdv should render the full-screen point of sale."""

    ProductRepository().insert_product(
        name="Item PDV Página", price=Decimal("3.00"), stock_quantity=4
    )

    response = logged_client.get("/pdv")

    assert response.status_code == 200
    page = response.get_data(as_text=True)
    assert 'id="pdv-search"' in page
    assert "Carrinho vazio" in page
    assert "Concluir venda" in page
    assert "F2" in page
    assert "Forma de pagamento" in page
    assert "Dinheiro" in page  # forma de pagamento padrão
    assert "Item PDV Página" in page  # produto embutido no JSON da busca


def test_complete_empty_cart(logged_client):
    """Finishing with an empty cart should not create an order."""

    token = _csrf(logged_client)
    before = len(OrderRepository().get_orders())

    logged_client.post(
        "/pdv/complete",
        data={"csrf_token": token, "payment_method_id": "1"},
        follow_redirects=True,
    )

    assert len(OrderRepository().get_orders()) == before


def test_complete_sale(logged_client):
    """Finishing a sale should create the order and decrement stock."""

    product = ProductRepository().insert_product(
        name="Item Venda Teste", price=Decimal("10.00"), stock_quantity=5
    )
    method = PaymentMethodRepository().get_active_methods()[0]
    token = _csrf(logged_client)

    response = logged_client.post(
        "/pdv/complete",
        data={
            "csrf_token": token,
            "payment_method_id": str(method.id),
            "product_id": str(product.id),
            "quantity": "2",
        },
        follow_redirects=False,
    )

    assert response.status_code == 302
    assert "/pdv/recibo/" in response.headers["Location"]
    assert ProductRepository().get_product(product.id).stock_quantity == 3


def test_complete_insufficient_stock(logged_client):
    """Finishing with insufficient stock should be rejected."""

    product = ProductRepository().insert_product(
        name="Item Insuficiente", price=Decimal("1.00"), stock_quantity=1
    )
    method = PaymentMethodRepository().get_active_methods()[0]
    token = _csrf(logged_client)

    response = logged_client.post(
        "/pdv/complete",
        data={
            "csrf_token": token,
            "payment_method_id": str(method.id),
            "product_id": str(product.id),
            "quantity": "5",
        },
        follow_redirects=True,
    )

    assert response.status_code == 200
    assert "Estoque insuficiente" in response.get_data(as_text=True)
    assert ProductRepository().get_product(product.id).stock_quantity == 1


def test_receipt_renders(logged_client):
    """GET /pdv/recibo/<id> should render the printable receipt."""

    product = ProductRepository().insert_product(
        name="Item Recibo Rota", price=Decimal("7.50"), stock_quantity=3
    )
    method = PaymentMethodRepository().get_active_methods()[0]
    order = OrderRepository().create_order([(product.id, 2)], method.id)

    response = logged_client.get(f"/pdv/recibo/{order.id}")

    assert response.status_code == 200
    page = response.get_data(as_text=True)
    assert f"#{order.id}" in page
    assert "Imprimir recibo" in page
    assert "Item Recibo Rota" in page
    assert method.name in page
