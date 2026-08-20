"""Tests for the PDV JSON API (SPA)."""

from decimal import Decimal

from billflux.infra.repository.payment_method_repository import (
    PaymentMethodRepository,
)
from billflux.infra.repository.product_repository import ProductRepository


def _csrf(client):
    response = client.get("/api/auth/csrf")
    assert response.status_code == 200
    return response.get_json()["csrf_token"]


def test_pdv_requires_login(client):
    """Sem sessão, /api/pdv deve devolver 401 JSON."""

    token = _csrf(client)
    assert client.get("/api/pdv").status_code == 401
    assert (
        client.post(
            "/api/pdv/complete", json={}, headers={"X-CSRFToken": token}
        ).status_code
        == 401
    )


def test_pdv_returns_products_and_methods(logged_client):
    """GET /api/pdv devolve produtos ativos e formas de pagamento ativas."""

    ProductRepository().insert_product(
        name="PDV Item", price=Decimal("5.00"), stock_quantity=3
    )
    response = logged_client.get("/api/pdv")

    assert response.status_code == 200
    data = response.get_json()
    product = next(p for p in data["products"] if p["name"] == "PDV Item")
    assert product["price"] == 5.0
    assert product["stock"] == 3
    assert data["methods"]  # formas padrão semeadas


def test_pdv_complete_creates_order(logged_client):
    """POST /complete finaliza a venda, baixa estoque e devolve o recibo."""

    product = ProductRepository().insert_product(
        name="PDV Venda", price=Decimal("10.00"), cost=Decimal("3.00"), stock_quantity=5
    )
    method = PaymentMethodRepository().get_active_methods()[0]
    token = _csrf(logged_client)

    response = logged_client.post(
        "/api/pdv/complete",
        json={
            "method_id": method.id,
            "obs": "Teste",
            "items": [{"product_id": product.id, "quantity": 2}],
        },
        headers={"X-CSRFToken": token},
    )

    assert response.status_code == 201
    order = response.get_json()["order"]
    assert order["total"] == 20.0
    assert order["payment_method"] == method.name
    assert order["obs"] == "Teste"
    assert order["items"][0]["name"] == "PDV Venda"
    assert order["items"][0]["subtotal"] == 20.0

    updated = ProductRepository().get_product(product.id)
    assert updated.stock_quantity == 3


def test_pdv_complete_validation(logged_client):
    """POST sem forma de pagamento, sem itens ou sem estoque devolve 400."""

    product = ProductRepository().insert_product(
        name="PDV Erro", price=Decimal("2.00"), stock_quantity=0
    )
    method = PaymentMethodRepository().get_active_methods()[0]
    token = _csrf(logged_client)

    no_method = logged_client.post(
        "/api/pdv/complete",
        json={"items": [{"product_id": product.id, "quantity": 1}]},
        headers={"X-CSRFToken": token},
    )
    assert no_method.status_code == 400

    no_items = logged_client.post(
        "/api/pdv/complete",
        json={"method_id": method.id, "items": []},
        headers={"X-CSRFToken": token},
    )
    assert no_items.status_code == 400

    no_stock = logged_client.post(
        "/api/pdv/complete",
        json={
            "method_id": method.id,
            "items": [{"product_id": product.id, "quantity": 1}],
        },
        headers={"X-CSRFToken": token},
    )
    assert no_stock.status_code == 400


def test_pdv_receipt(logged_client):
    """GET /api/pdv/recibo/<id> devolve os dados de um pedido."""

    product = ProductRepository().insert_product(
        name="PDV Recibo", price=Decimal("7.50"), stock_quantity=4
    )
    method = PaymentMethodRepository().get_active_methods()[0]
    token = _csrf(logged_client)

    created = logged_client.post(
        "/api/pdv/complete",
        json={
            "method_id": method.id,
            "items": [{"product_id": product.id, "quantity": 1}],
        },
        headers={"X-CSRFToken": token},
    ).get_json()
    order_id = created["order"]["order_id"]

    response = logged_client.get(f"/api/pdv/recibo/{order_id}")

    assert response.status_code == 200
    order = response.get_json()["order"]
    assert order["order_id"] == order_id
    assert order["total"] == 7.5

    missing = logged_client.get("/api/pdv/recibo/999999")
    assert missing.status_code == 404
