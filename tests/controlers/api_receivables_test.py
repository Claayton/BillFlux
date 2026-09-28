"""Tests for fiado/credit (receivables) JSON APIs."""

from decimal import Decimal

from billflux.infra.repository.customer_repository import CustomerRepository
from billflux.infra.repository.payment_method_repository import (
    PaymentMethodRepository,
)
from billflux.infra.repository.product_repository import ProductRepository
from billflux.infra.repository.receivable_repository import ReceivableRepository


def _csrf(client):
    response = client.get("/api/auth/csrf")
    assert response.status_code == 200
    return response.get_json()["csrf_token"]


def _login(client):
    return client.post(
        "/api/auth/login",
        json={"username": "admin", "password": "admin"},
        headers={"X-CSRFToken": _csrf(client)},
    )


def _open_caixa(client, amount="100.00"):
    token = _csrf(client)
    response = client.post(
        "/api/caixa/open",
        json={"opening_details": {"1": amount}},
        headers={"X-CSRFToken": token},
    )
    assert response.status_code == 201
    return response.get_json()


def _close_caixa(client):
    status = client.get("/api/caixa").get_json()
    if not status.get("open"):
        return None
    response = client.post(
        "/api/caixa/close",
        json={"closing_details": {}},
        headers={"X-CSRFToken": _csrf(client)},
    )
    assert response.status_code == 200
    return response.get_json()["last_closed"]


def _fiado_method():
    methods = PaymentMethodRepository().get_methods()
    fiado = next((m for m in methods if m.name == "Fiado"), None)
    assert fiado is not None, "forma 'Fiado' deve existir (seed)"
    return fiado


def _dinheiro_method():
    return next(
        m for m in PaymentMethodRepository().get_methods() if m.name == "Dinheiro"
    )


def _create_customer(client, name):
    response = client.post(
        "/api/customers",
        json={"name": name},
        headers={"X-CSRFToken": _csrf(client)},
    )
    assert response.status_code == 201
    customers = response.get_json()["customers"]
    return next(c for c in customers if c["name"] == name)


def _create_product(name, price="10.00", stock=10):
    return ProductRepository().insert_product(
        name=name, price=Decimal(price), stock_quantity=stock
    )


def _fiado_sale(client, product, customer_id, amount, payments=None):
    fiado = _fiado_method()
    payload = {
        "customer_id": customer_id,
        "items": [{"product_id": product.id, "quantity": 1}],
        "payments": payments or [{"method_id": fiado.id, "amount": amount}],
    }
    return client.post(
        "/api/pdv/complete",
        json=payload,
        headers={"X-CSRFToken": _csrf(client)},
    )


def test_fiado_method_is_seeded(client):
    """A forma de pagamento 'Fiado' é criada automaticamente no startup."""
    assert _login(client).status_code == 200
    assert _fiado_method()


def test_fiado_sale_creates_debit(client):
    """Venda fiada gera débito, badge no cliente e NÃO conta no esperado."""

    assert _login(client).status_code == 200
    _close_caixa(client)
    _open_caixa(client, amount="100.00")

    customer = _create_customer(client, "Cliente Fiado")
    product = _create_product("Produto Fiado", price="20.00")

    response = _fiado_sale(client, product, customer["id"], "20.00")
    assert response.status_code == 201
    order_id = response.get_json()["order"]["order_id"]

    receivables = client.get("/api/receivables").get_json()
    item = next(r for r in receivables["items"] if r["order_id"] == order_id)
    assert item["customer_id"] == customer["id"]
    assert item["amount"] == 20.0
    assert item["paid"] == 0.0
    assert item["balance"] == 20.0
    assert receivables["totals"]["open_amount"] >= 20.0

    customers = client.get("/api/customers").get_json()["customers"]
    badge = next(c for c in customers if c["id"] == customer["id"])
    assert badge["credit_balance"] == 20.0

    # fiado não é dinheiro esperado no caixa
    caixa = client.get("/api/caixa").get_json()
    fiado_id = _fiado_method().id
    assert str(fiado_id) not in caixa["system_totals"]

    closed = _close_caixa(client)
    assert closed["expected_amount"] == 100.0


def test_fiado_sale_requires_customer(client):
    """Venda fiada sem cliente é recusada."""

    assert _login(client).status_code == 200
    _close_caixa(client)
    _open_caixa(client, amount="50.00")

    product = _create_product("Produto Sem Cliente", price="10.00")
    fiado = _fiado_method()

    response = client.post(
        "/api/pdv/complete",
        json={
            "payments": [{"method_id": fiado.id, "amount": "10.00"}],
            "items": [{"product_id": product.id, "quantity": 1}],
        },
        headers={"X-CSRFToken": _csrf(client)},
    )
    assert response.status_code == 400
    assert "cliente" in response.get_json()["error"].lower()

    _close_caixa(client)


def test_receivable_payment_enters_caixa(client):
    """Recebimento reduz saldo, vira 'entrada' no caixa e valida limites."""

    assert _login(client).status_code == 200
    _close_caixa(client)
    _open_caixa(client, amount="100.00")

    customer = _create_customer(client, "Cliente Recebe")
    product = _create_product("Produto Recebe", price="30.00")
    sale = _fiado_sale(client, product, customer["id"], "30.00")
    assert sale.status_code == 201
    receivable_id = next(
        r["id"]
        for r in client.get("/api/receivables").get_json()["items"]
        if r["customer_name"] == "Cliente Recebe"
    )
    token = _csrf(client)

    # sem forma de pagamento → 400
    bad = client.post(
        f"/api/receivables/{receivable_id}/payments",
        json={"amount": "10.00"},
        headers={"X-CSRFToken": token},
    )
    assert bad.status_code == 400

    # acima do saldo → 400
    over = client.post(
        f"/api/receivables/{receivable_id}/payments",
        json={"amount": "50.00", "method_id": _dinheiro_method().id},
        headers={"X-CSRFToken": token},
    )
    assert over.status_code == 400

    ok = client.post(
        f"/api/receivables/{receivable_id}/payments",
        json={"amount": "10.00", "method_id": _dinheiro_method().id},
        headers={"X-CSRFToken": token},
    )
    assert ok.status_code == 200
    data = ok.get_json()
    assert data["in_caixa"] is True
    assert data["receivable"]["paid"] == 10.0
    assert data["receivable"]["balance"] == 20.0

    caixa = client.get("/api/caixa").get_json()
    assert caixa["movement_totals"]["entrada"] == 10.0
    assert caixa["movements"][0]["kind"] == "entrada"
    assert "Cliente Recebe" in caixa["movements"][0]["obs"]

    # quita o resto e confere filtro de status
    client.post(
        f"/api/receivables/{receivable_id}/payments",
        json={"amount": "20.00", "method_id": _dinheiro_method().id},
        headers={"X-CSRFToken": _csrf(client)},
    )
    open_ids = [r["id"] for r in client.get("/api/receivables").get_json()["items"]]
    assert receivable_id not in open_ids
    paid_ids = [
        r["id"] for r in client.get("/api/receivables?status=paid").get_json()["items"]
    ]
    assert receivable_id in paid_ids

    closed = _close_caixa(client)
    # abertura 100 + fiado fora + entradas 30 = 130
    assert closed["expected_amount"] == 130.0


def test_cancel_order_cancels_debit(client):
    """Cancelar venda fiada cancela o débito e audita."""

    assert _login(client).status_code == 200
    _close_caixa(client)
    _open_caixa(client, amount="10.00")

    customer = _create_customer(client, "Cliente Cancela")
    product = _create_product("Produto Cancela", price="15.00")
    sale = _fiado_sale(client, product, customer["id"], "15.00")
    order_id = sale.get_json()["order"]["order_id"]

    cancel = client.post(
        f"/api/sales/orders/{order_id}/cancel",
        json={"reason": "cliente desistiu"},
        headers={"X-CSRFToken": _csrf(client)},
    )
    assert cancel.status_code == 200

    open_items = client.get("/api/receivables").get_json()["items"]
    assert all(r["order_id"] != order_id for r in open_items)

    customers = client.get("/api/customers").get_json()["customers"]
    badge = next(c for c in customers if c["id"] == customer["id"])
    assert badge["credit_balance"] == 0.0

    events = client.get("/api/audit?entity=receivable").get_json()["events"]
    assert any(e["action"] == "credit.cancel" for e in events)

    _close_caixa(client)


def test_order_edit_reconciles_debit(client):
    """Editar venda: p/ fora de fiado cancela débito; p/ fiado exige cliente."""

    assert _login(client).status_code == 200
    _close_caixa(client)
    _open_caixa(client, amount="10.00")

    customer = _create_customer(client, "Cliente Edita")
    product = _create_product("Produto Edita", price="25.00")

    # venda fiada → editar para dinheiro cancela o débito
    sale = _fiado_sale(client, product, customer["id"], "25.00")
    order_id = sale.get_json()["order"]["order_id"]
    edit = client.put(
        f"/api/sales/orders/{order_id}",
        json={
            "method_id": _dinheiro_method().id,
            "items": [{"product_id": product.id, "quantity": 1}],
        },
        headers={"X-CSRFToken": _csrf(client)},
    )
    assert edit.status_code == 200
    open_items = client.get("/api/receivables").get_json()["items"]
    assert all(r["order_id"] != order_id for r in open_items)

    # venda em dinheiro sem cliente → editar para fiado é recusado
    plain = client.post(
        "/api/pdv/complete",
        json={
            "method_id": _dinheiro_method().id,
            "items": [{"product_id": product.id, "quantity": 1}],
        },
        headers={"X-CSRFToken": _csrf(client)},
    )
    assert plain.status_code == 201
    plain_id = plain.get_json()["order"]["order_id"]
    edit2 = client.put(
        f"/api/sales/orders/{plain_id}",
        json={
            "method_id": _fiado_method().id,
            "items": [{"product_id": product.id, "quantity": 1}],
        },
        headers={"X-CSRFToken": _csrf(client)},
    )
    assert edit2.status_code == 400
    assert "cliente" in edit2.get_json()["error"].lower()

    # venda em dinheiro COM cliente → editar para fiado cria o débito
    with_customer = client.post(
        "/api/pdv/complete",
        json={
            "method_id": _dinheiro_method().id,
            "customer_id": customer["id"],
            "items": [{"product_id": product.id, "quantity": 1}],
        },
        headers={"X-CSRFToken": _csrf(client)},
    )
    assert with_customer.status_code == 201
    wc_id = with_customer.get_json()["order"]["order_id"]
    edit3 = client.put(
        f"/api/sales/orders/{wc_id}",
        json={
            "method_id": _fiado_method().id,
            "customer_id": customer["id"],
            "items": [{"product_id": product.id, "quantity": 1}],
        },
        headers={"X-CSRFToken": _csrf(client)},
    )
    assert edit3.status_code == 200
    wc_items = [
        r
        for r in client.get("/api/receivables").get_json()["items"]
        if r["order_id"] == wc_id
    ]
    assert len(wc_items) == 1
    assert wc_items[0]["balance"] == 25.0

    _close_caixa(client)


def test_receivables_validation(client):
    """Validações de filtro e débito inexistente."""

    assert _login(client).status_code == 200

    assert client.get("/api/receivables?status=xyz").status_code == 400
    assert (
        client.post(
            "/api/receivables/999999/payments",
            json={"amount": "1.00", "method_id": _dinheiro_method().id},
            headers={"X-CSRFToken": _csrf(client)},
        ).status_code
        == 404
    )

    # saldo devedor consolidado por cliente
    balances = ReceivableRepository().customer_balances()
    for value in balances.values():
        assert value > 0
