"""Tests from the products routes"""

import re
from decimal import Decimal

from billflux.infra.repository.order_repository import OrderRepository
from billflux.infra.repository.payment_method_repository import PaymentMethodRepository
from billflux.infra.repository.product_repository import ProductRepository


def _csrf(client):
    page = client.get("/products")
    match = re.search(r'name="csrf_token" value="([^"]+)"', page.get_data(as_text=True))
    assert match, "CSRF token not found in /products page"
    return match.group(1)


def test_products_requires_login(client):
    """Unauthenticated users should be redirected to login."""

    response = client.get("/products")

    assert response.status_code == 302
    assert "/login" in response.headers["Location"]


def test_products_page(logged_client):
    """GET /products should render the catalog page."""

    response = logged_client.get("/products")

    assert response.status_code == 200
    page = response.get_data(as_text=True)
    assert "Produtos" in page
    assert "Novo produto" in page
    assert "Código de barras" in page


def test_create_product(logged_client):
    """POSTing a valid product should persist it."""

    token = _csrf(logged_client)
    logged_client.post(
        "/products/new",
        data={
            "csrf_token": token,
            "name": "Produto do Teste",
            "price": "12,50",
            "cost": "8,00",
            "barcode": "999000111",
            "stock_quantity": "10",
            "min_stock": "2",
            "obs": "Teste",
            "active": "on",
        },
        follow_redirects=True,
    )

    product = ProductRepository().get_product_by_barcode("999000111")
    assert product is not None
    assert product.name == "Produto do Teste"
    assert product.price == Decimal("12.50")
    assert product.cost == Decimal("8.00")
    assert product.stock_quantity == 10


def test_create_product_shows_cost(logged_client):
    """The catalog page should display the cost column and value."""

    ProductRepository().insert_product(
        name="Com Custo", price=Decimal("20.00"), cost=Decimal("15.50")
    )

    response = logged_client.get("/products")

    assert response.status_code == 200
    page = response.get_data(as_text=True)
    assert "Custo" in page
    assert "R$ 15,50" in page


def test_create_product_invalid(logged_client):
    """POSTing without a name or price should not persist anything."""

    token = _csrf(logged_client)
    logged_client.post(
        "/products/new",
        data={"csrf_token": token, "name": "", "price": ""},
        follow_redirects=True,
    )

    assert ProductRepository().get_product_by_barcode("999000222") is None


def test_adjust_stock_route(logged_client):
    """POSTing an adjustment should change stock."""

    product = ProductRepository().insert_product(
        name="Ajuste via Rota", price=Decimal("3.00"), stock_quantity=5
    )
    token = _csrf(logged_client)

    response = logged_client.post(
        "/products/adjust",
        data={
            "csrf_token": token,
            "product_id": str(product.id),
            "delta": "5",
            "obs": "Entrada",
        },
        follow_redirects=True,
    )

    assert response.status_code == 200
    assert ProductRepository().get_product(product.id).stock_quantity == 10


def test_delete_product_blocked_when_sold(logged_client):
    """A product already sold cannot be deleted."""

    product = ProductRepository().insert_product(
        name="Vendido Delete", price=Decimal("2.00"), stock_quantity=5
    )
    method = PaymentMethodRepository().get_active_methods()[0]
    OrderRepository().create_order([(product.id, 1)], method.id)

    token = _csrf(logged_client)
    logged_client.post(
        f"/products/delete/{product.id}",
        headers={"X-CSRFToken": token},
        follow_redirects=True,
    )

    assert ProductRepository().get_product(product.id) is not None


def test_movements_fragment(logged_client):
    """GET /products/movements/<id> should render recent movements."""

    product = ProductRepository().insert_product(
        name="Fragmento", price=Decimal("1.00"), stock_quantity=3
    )

    response = logged_client.get(f"/products/movements/{product.id}")

    assert response.status_code == 200
    assert "entrada" in response.get_data(as_text=True).lower()
