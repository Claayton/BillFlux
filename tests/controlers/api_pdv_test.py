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


def _open_caixa(client):
    """Abre um caixa no banco de testes pra permitir vendas."""
    from billflux.infra.config.database import get_session
    from billflux.infra.entities.cash_register import CashRegister
    from sqlmodel import select

    session = get_session()
    with session:
        existing = session.exec(
            select(CashRegister).where(CashRegister.status == "open")
        ).first()
        if existing:
            existing.status = "closed"
            existing.closed_by = "test"
            existing.closed_at = "2026-08-23 00:00:00"
            existing.closing_amount = existing.opening_amount
            existing.expected_amount = existing.opening_amount
            session.add(existing)
            session.commit()
        cr = CashRegister(
            opened_by="test",
            opened_at="2026-08-23 00:00:00",
            opening_amount=100.0,
            status="open",
        )
        session.add(cr)
        session.commit()


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

    _open_caixa(logged_client)
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
    """POST sem forma de pagamento ou sem itens devolve 400."""

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


def test_pdv_complete_without_stock_allows_negative(logged_client):
    """Venda sem estoque é permitida e deixa o estoque negativo."""

    _open_caixa(logged_client)
    product = ProductRepository().insert_product(
        name="Sem Estoque", price=Decimal("2.00"), stock_quantity=0
    )
    method = PaymentMethodRepository().get_active_methods()[0]
    token = _csrf(logged_client)

    response = logged_client.post(
        "/api/pdv/complete",
        json={
            "method_id": method.id,
            "items": [{"product_id": product.id, "quantity": 3}],
        },
        headers={"X-CSRFToken": token},
    )

    assert response.status_code == 201
    assert response.get_json()["order"]["total"] == 6.0
    updated = ProductRepository().get_product(product.id)
    assert updated.stock_quantity == -3


def test_pdv_complete_with_discount(logged_client):
    """POST /complete aceita desconto e o abate do total e do recibo."""

    _open_caixa(logged_client)
    product = ProductRepository().insert_product(
        name="PDV Desconto", price=Decimal("10.00"), stock_quantity=5
    )
    method = PaymentMethodRepository().get_active_methods()[0]
    token = _csrf(logged_client)

    response = logged_client.post(
        "/api/pdv/complete",
        json={
            "method_id": method.id,
            "items": [{"product_id": product.id, "quantity": 2}],
            "discount": 5,
        },
        headers={"X-CSRFToken": token},
    )

    assert response.status_code == 201
    order = response.get_json()["order"]
    assert order["total"] == 15.0  # 20 - 5
    assert order["discount"] == 5.0

    invalid = logged_client.post(
        "/api/pdv/complete",
        json={
            "method_id": method.id,
            "items": [{"product_id": product.id, "quantity": 1}],
            "discount": -1,
        },
        headers={"X-CSRFToken": token},
    )
    assert invalid.status_code == 400


def test_pdv_complete_split_payments(logged_client):
    """POST /complete aceita pagamento dividido entre formas de pagamento."""

    _open_caixa(logged_client)
    product = ProductRepository().insert_product(
        name="PDV Split", price=Decimal("2.00"), stock_quantity=5
    )
    methods = PaymentMethodRepository().get_active_methods()
    cash, pix = methods[0], methods[1]
    token = _csrf(logged_client)

    response = logged_client.post(
        "/api/pdv/complete",
        json={
            "payments": [
                {"method_id": cash.id, "amount": "2.00"},
                {"method_id": pix.id, "amount": "2.00"},
            ],
            "items": [{"product_id": product.id, "quantity": 2}],
        },
        headers={"X-CSRFToken": token},
    )

    assert response.status_code == 201
    order = response.get_json()["order"]
    assert order["total"] == 4.0
    assert len(order["payments"]) == 2
    assert order["payment_method"] == cash.name
    assert {p["name"] for p in order["payments"]} == {cash.name, pix.name}
    assert sorted(p["amount"] for p in order["payments"]) == [2.0, 2.0]

    updated = ProductRepository().get_product(product.id)
    assert updated.stock_quantity == 3


def test_pdv_complete_split_payments_validation(logged_client):
    """Pagamento dividido com valores insuficientes ou forma inválida falha."""

    product = ProductRepository().insert_product(
        name="PDV Split Erro", price=Decimal("5.00"), stock_quantity=3
    )
    methods = PaymentMethodRepository().get_active_methods()
    cash, pix = methods[0], methods[1]
    token = _csrf(logged_client)

    insufficient = logged_client.post(
        "/api/pdv/complete",
        json={
            "payments": [
                {"method_id": cash.id, "amount": "2.00"},
                {"method_id": pix.id, "amount": "1.00"},
            ],
            "items": [{"product_id": product.id, "quantity": 2}],
        },
        headers={"X-CSRFToken": token},
    )
    assert insufficient.status_code == 400

    invalid_method = logged_client.post(
        "/api/pdv/complete",
        json={
            "payments": [{"method_id": 999999, "amount": "10.00"}],
            "items": [{"product_id": product.id, "quantity": 2}],
        },
        headers={"X-CSRFToken": token},
    )
    assert invalid_method.status_code == 400

    zero_amount = logged_client.post(
        "/api/pdv/complete",
        json={
            "payments": [{"method_id": cash.id, "amount": "0"}],
            "items": [{"product_id": product.id, "quantity": 2}],
        },
        headers={"X-CSRFToken": token},
    )
    assert zero_amount.status_code == 400


def test_pdv_complete_with_change(logged_client):
    """Recibo informa quanto foi pago em cada forma e o troco."""

    _open_caixa(logged_client)
    product = ProductRepository().insert_product(
        name="PDV Troco", price=Decimal("2.00"), stock_quantity=5
    )
    methods = PaymentMethodRepository().get_active_methods()
    cash = methods[0]
    token = _csrf(logged_client)

    response = logged_client.post(
        "/api/pdv/complete",
        json={
            "payments": [{"method_id": cash.id, "amount": "10.00"}],
            "items": [{"product_id": product.id, "quantity": 2}],
        },
        headers={"X-CSRFToken": token},
    )

    assert response.status_code == 201
    order = response.get_json()["order"]
    assert order["total"] == 4.0
    assert order["payments"] == [
        {"method_id": cash.id, "name": cash.name, "amount": 10.0}
    ]
    assert order["troco"] == 6.0


def test_pdv_receipt(logged_client):
    """GET /api/pdv/recibo/<id> devolve os dados de um pedido."""

    _open_caixa(logged_client)
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
