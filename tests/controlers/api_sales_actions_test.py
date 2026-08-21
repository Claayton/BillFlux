"""Tests for sales actions: edit manual, cancel/edit PDV and manual receipt."""

from decimal import Decimal

from billflux.infra.repository.payment_method_repository import (
    PaymentMethodRepository,
)
from billflux.infra.repository.product_repository import ProductRepository
from billflux.infra.repository.order_repository import OrderRepository
from billflux.infra.repository.sale_repository import SaleRepository


def _csrf(client):
    response = client.get("/api/auth/csrf")
    assert response.status_code == 200
    return response.get_json()["csrf_token"]


def _make_order(name="Item PDV", price="10.00", qty=3, stock=10):
    product = ProductRepository().insert_product(
        name=name, price=Decimal(price), stock_quantity=stock
    )
    method = PaymentMethodRepository().get_active_methods()[0]
    order = OrderRepository().create_order([(product.id, qty)], method.id)
    return product, method, order


def test_edit_manual_sale(logged_client):
    """PUT /api/sales/<id> edita valor, data e observações da venda avulsa."""

    token = _csrf(logged_client)
    SaleRepository().insert_sale(
        __import__("datetime").date(2026, 7, 10), Decimal("100.00"), "Antes"
    )
    created = logged_client.get("/api/sales").get_json()
    sale = next(s for s in created["sales"] if s["kind"] == "manual")

    response = logged_client.put(
        f"/api/sales/{sale['id']}",
        json={"date": "2026-07-12", "total": "150,50", "obs": "Depois"},
        headers={"X-CSRFToken": token},
    )

    assert response.status_code == 200
    sales = response.get_json()["sales"]
    edited = next(
        s for s in sales if s["kind"] == "manual" and s["date"] == "2026-07-12"
    )
    assert edited["total"] == 150.5
    assert edited["obs"] == "Depois"

    missing = logged_client.put(
        "/api/sales/999999",
        json={"date": "2026-07-12", "total": "10,00"},
        headers={"X-CSRFToken": token},
    )
    assert missing.status_code == 404


def test_cancel_order_restores_stock(logged_client):
    """DELETE /api/sales/orders/<id> cancela e devolve o estoque."""

    token = _csrf(logged_client)
    product, _method, order = _make_order(qty=3, stock=10)

    response = logged_client.delete(
        f"/api/sales/orders/{order.id}", headers={"X-CSRFToken": token}
    )

    assert response.status_code == 200
    assert OrderRepository().get_order(order.id) is None
    updated = ProductRepository().get_product(product.id)
    assert updated.stock_quantity == 10  # estoque restaurado


def test_edit_order_keeps_id_and_adjusts_stock(logged_client):
    """PUT /api/sales/orders/<id> edita itens mantendo o id e o estoque certo."""

    token = _csrf(logged_client)
    product, method, order = _make_order(qty=2, stock=10)

    response = logged_client.put(
        f"/api/sales/orders/{order.id}",
        json={
            "method_id": method.id,
            "items": [{"product_id": product.id, "quantity": 5}],
            "obs": "Editado",
        },
        headers={"X-CSRFToken": token},
    )

    assert response.status_code == 200
    sales = response.get_json()["sales"]
    edited = next(s for s in sales if s["kind"] == "pdv" and s["id"] == order.id)
    assert edited["total"] == 50.0  # 5 * 10
    assert edited["obs"] == "Editado"
    assert edited["items"][0]["quantity"] == 5
    updated = ProductRepository().get_product(product.id)
    assert updated.stock_quantity == 5  # 10 - (5 - 2)


def test_edit_order_validation(logged_client):
    """PUT sem forma de pagamento, sem itens ou sem estoque devolve 400."""

    token = _csrf(logged_client)
    product, _method, order = _make_order(qty=1, stock=1)
    method = PaymentMethodRepository().get_active_methods()[0]

    no_method = logged_client.put(
        f"/api/sales/orders/{order.id}",
        json={"items": [{"product_id": product.id, "quantity": 1}]},
        headers={"X-CSRFToken": token},
    )
    assert no_method.status_code == 400

    no_items = logged_client.put(
        f"/api/sales/orders/{order.id}",
        json={"method_id": method.id, "items": []},
        headers={"X-CSRFToken": token},
    )
    assert no_items.status_code == 400

    # Aumenta para 5 mas só há 1 de estoque (1 já está no pedido).
    no_stock = logged_client.put(
        f"/api/sales/orders/{order.id}",
        json={
            "method_id": method.id,
            "items": [{"product_id": product.id, "quantity": 5}],
        },
        headers={"X-CSRFToken": token},
    )
    assert no_stock.status_code == 400


def test_manual_receipt(logged_client):
    """GET /api/sales/recibo/<id> devolve o recibo da venda avulsa."""

    sale = SaleRepository().insert_sale(
        __import__("datetime").date(2026, 7, 10), Decimal("80.00"), "Feira"
    )

    response = logged_client.get(f"/api/sales/recibo/{sale.id}")

    assert response.status_code == 200
    order = response.get_json()["order"]
    assert order["order_id"] == sale.id
    assert order["total"] == 80.0
    assert order["items"][0]["name"] == "Venda avulsa"
    assert order["items"][0]["subtotal"] == 80.0

    missing = logged_client.get("/api/sales/recibo/999999")
    assert missing.status_code == 404


def test_sales_list_includes_time_items_payment(logged_client):
    """A lista agora traz hora, itens e forma de pagamento."""

    product = ProductRepository().insert_product(
        name="Com Item", price=Decimal("4.00"), stock_quantity=5
    )
    method = PaymentMethodRepository().get_active_methods()[0]
    OrderRepository().create_order([(product.id, 2)], method.id)

    response = logged_client.get("/api/sales")
    data = response.get_json()
    pdv = next(s for s in data["sales"] if s["kind"] == "pdv")
    assert pdv["payment"] == method.name
    assert pdv["time"] is not None
    assert any(i["name"] == "Com Item" and i["quantity"] == 2 for i in pdv["items"])
    manual = next(s for s in data["sales"] if s["kind"] == "manual")
    assert manual["items"] == []
    assert manual["time"] is None
