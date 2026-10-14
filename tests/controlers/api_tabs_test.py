"""Tests for tabs (comandas) JSON APIs."""

from decimal import Decimal

from billflux.infra.repository.payment_method_repository import (
    PaymentMethodRepository,
)
from billflux.infra.repository.product_repository import ProductRepository


def _csrf(client):
    response = client.get("/api/auth/csrf")
    assert response.status_code == 200
    return response.get_json()["csrf_token"]


def _set_caixa(open_register: bool):
    """Abre ou fecha o caixa direto no banco (padrão dos testes do PDV)."""
    from billflux.infra.config.database import get_session
    from billflux.infra.entities.cash_register import CashRegister
    from sqlmodel import select

    session = get_session()
    with session:
        for cr in session.exec(
            select(CashRegister).where(CashRegister.status == "open")
        ):
            cr.status = "closed"
            cr.closed_by = "test"
            cr.closed_at = "2026-08-23 00:00:00"
            cr.closing_amount = cr.opening_amount
            cr.expected_amount = cr.opening_amount
            session.add(cr)
        if open_register:
            session.add(
                CashRegister(
                    opened_by="test",
                    opened_at="2026-08-23 00:00:00",
                    opening_amount=100.0,
                    status="open",
                )
            )
        session.commit()


def _open_caixa():
    _set_caixa(True)


def _product(name, price="5.00", stock=10):
    return ProductRepository().insert_product(
        name=name, price=Decimal(price), stock_quantity=stock
    )


def _method(name):
    methods = PaymentMethodRepository().get_methods()
    method = next((m for m in methods if m.name == name), None)
    assert method is not None, f"forma '{name}' deve existir"
    return method


def _open_tab(client, identification, product, quantity=2, unit_id=None):
    token = _csrf(client)
    item = {"product_id": product.id, "quantity": quantity}
    if unit_id:
        item["unit_id"] = unit_id
    response = client.post(
        "/api/tabs",
        json={"identification": identification, "items": [item]},
        headers={"X-CSRFToken": token},
    )
    assert response.status_code == 201, response.get_json()
    return response.get_json()["tab"]


def _stock(product_id):
    return ProductRepository().get_product(product_id).stock_quantity


def _movements(product_id):
    from billflux.infra.config.database import get_session
    from billflux.infra.entities.product_movement import ProductMovement
    from sqlmodel import select

    session = get_session()
    try:
        return session.exec(
            select(ProductMovement)
            .where(ProductMovement.product_id == product_id)
            .order_by(ProductMovement.id)
        ).all()
    finally:
        session.close()


def test_tabs_require_login(client):
    """Sem sessão, os endpoints de comanda devolvem 401 JSON."""

    token = _csrf(client)
    assert client.get("/api/tabs").status_code == 401
    assert (
        client.post("/api/tabs", json={}, headers={"X-CSRFToken": token}).status_code
        == 401
    )
    assert client.get("/api/tabs/1").status_code == 401
    assert (
        client.post(
            "/api/tabs/1/close", json={}, headers={"X-CSRFToken": token}
        ).status_code
        == 401
    )


def test_create_tab_validation(logged_client):
    """Abertura valida identificação obrigatória, itens e produtos."""

    product = _product("Tab Validacao", "3.00", 5)
    token = _csrf(logged_client)

    no_identification = logged_client.post(
        "/api/tabs",
        json={
            "identification": "  ",
            "items": [{"product_id": product.id, "quantity": 1}],
        },
        headers={"X-CSRFToken": token},
    )
    assert no_identification.status_code == 400
    assert (
        no_identification.get_json()["error"] == "Informe a identificação da comanda."
    )

    no_items = logged_client.post(
        "/api/tabs",
        json={"identification": "Mesa 1", "items": []},
        headers={"X-CSRFToken": token},
    )
    assert no_items.status_code == 400

    invalid_product = logged_client.post(
        "/api/tabs",
        json={
            "identification": "Mesa 1",
            "items": [{"product_id": 999999, "quantity": 1}],
        },
        headers={"X-CSRFToken": token},
    )
    assert invalid_product.status_code == 400
    assert invalid_product.get_json()["error"] == "Produto não encontrado."

    invalid_qty = logged_client.post(
        "/api/tabs",
        json={
            "identification": "Mesa 1",
            "items": [{"product_id": product.id, "quantity": 0}],
        },
        headers={"X-CSRFToken": token},
    )
    assert invalid_qty.status_code == 400

    assert _stock(product.id) == 5  # nada foi persistido


def test_create_tab_decrements_stock_and_registers(logged_client):
    """Abrir comanda baixa o estoque, snapshota itens e registra auditoria."""

    product = _product("Tab Estoque", "4.00", 10)

    first = _open_tab(logged_client, "Mesa 2", product, quantity=3)
    assert first["status"] == "open"
    assert first["label"] == f"#{first['number']:04d}"
    assert first["identification"] == "Mesa 2"
    assert first["total"] == 12.0
    assert first["subtotal"] == 12.0
    assert first["order_id"] is None
    assert first["print_count"] == 0
    assert first["item_count"] == 1
    assert first["units_count"] == 3
    assert first["items"][0]["name"] == "Tab Estoque"
    assert first["items"][0]["quantity"] == 3
    assert first["items"][0]["unit_price"] == 4.0
    assert first["opened_by"] == "admin"

    assert _stock(product.id) == 7  # baixa na abertura

    movements = [m for m in _movements(product.id) if m.obs != "Estoque inicial"]
    assert len(movements) == 1
    assert movements[0].movement_type == "saida"
    assert movements[0].quantity == 3
    assert movements[0].obs == f"Comanda #{first['number']:04d}"

    second = _open_tab(logged_client, "João", product, quantity=1)
    assert second["number"] > first["number"]  # sequencial monotônico
    assert _stock(product.id) == 6

    events = logged_client.get("/api/audit?entity=tab").get_json()["events"]
    opens = [e for e in events if e["action"] == "tab.open"]
    assert opens and opens[-1]["entity_id"] == first["id"]


def test_list_and_search_tabs(logged_client):
    """Lista comandas abertas com contadores; busca por número/identificação."""

    product = _product("Tab Lista", "2.00", 10)
    mesa = _open_tab(logged_client, "Mesa 10", product, quantity=2)
    joao = _open_tab(logged_client, "João", product, quantity=1)

    open_tabs = logged_client.get("/api/tabs").get_json()["tabs"]
    ids = {t["id"] for t in open_tabs}
    assert {mesa["id"], joao["id"]} <= ids
    listed = next(t for t in open_tabs if t["id"] == mesa["id"])
    assert listed["item_count"] == 1
    assert listed["units_count"] == 2
    assert listed["opened_at"]

    by_name = logged_client.get("/api/tabs?q=Mesa 10").get_json()["tabs"]
    assert [t["id"] for t in by_name] == [mesa["id"]]

    by_number = logged_client.get(f"/api/tabs?q={joao['number']}").get_json()["tabs"]
    assert [t["id"] for t in by_number] == [joao["id"]]

    # cancelada sai do padrão (abertas) mas continua no histórico
    logged_client.post(
        f"/api/tabs/{joao['id']}/cancel", headers={"X-CSRFToken": _csrf(logged_client)}
    )
    open_ids = {t["id"] for t in logged_client.get("/api/tabs").get_json()["tabs"]}
    assert joao["id"] not in open_ids
    all_ids = {
        t["id"] for t in logged_client.get("/api/tabs?status=all").get_json()["tabs"]
    }
    assert joao["id"] in all_ids

    invalid = logged_client.get("/api/tabs?status=foo")
    assert invalid.status_code == 400


def test_get_tab_detail(logged_client):
    """GET /tabs/<id> devolve a comanda com itens; inexistente devolve 404."""

    product = _product("Tab Detalhe", "6.00", 4)
    tab = _open_tab(logged_client, "Mesa 3", product, quantity=2)

    detail = logged_client.get(f"/api/tabs/{tab['id']}")
    assert detail.status_code == 200
    body = detail.get_json()["tab"]
    assert body["number"] == tab["number"]
    assert len(body["items"]) == 1
    assert body["items"][0]["product_id"] == product.id

    missing = logged_client.get("/api/tabs/999999")
    assert missing.status_code == 404


def test_set_tab_items_applies_stock_deltas(logged_client):
    """Atualizar itens aplica delta por produto (adiciona baixa, remove devolve)."""

    product_a = _product("Tab Delta A", "5.00", 10)
    product_b = _product("Tab Delta B", "3.00", 5)
    tab = _open_tab(logged_client, "Mesa 4", product_a, quantity=2)
    assert _stock(product_a.id) == 8

    token = _csrf(logged_client)

    # adiciona 1 de A e 1 de B
    response = logged_client.put(
        f"/api/tabs/{tab['id']}/items",
        json={
            "items": [
                {"product_id": product_a.id, "quantity": 3},
                {"product_id": product_b.id, "quantity": 1},
            ]
        },
        headers={"X-CSRFToken": token},
    )
    assert response.status_code == 200
    updated = response.get_json()["tab"]
    assert updated["total"] == 18.0  # 15 + 3
    assert _stock(product_a.id) == 7
    assert _stock(product_b.id) == 4

    # remove A (devolve 3)
    logged_client.put(
        f"/api/tabs/{tab['id']}/items",
        json={"items": [{"product_id": product_b.id, "quantity": 1}]},
        headers={"X-CSRFToken": token},
    )
    assert _stock(product_a.id) == 10
    assert _stock(product_b.id) == 4
    empty_movements = [
        m for m in _movements(product_a.id) if m.movement_type == "entrada"
    ]
    assert empty_movements and "item removido" in (empty_movements[-1].obs or "")

    # esvazia a comanda (devolve B)
    emptied = logged_client.put(
        f"/api/tabs/{tab['id']}/items",
        json={"items": []},
        headers={"X-CSRFToken": token},
    )
    assert emptied.status_code == 200
    assert emptied.get_json()["tab"]["total"] == 0.0
    assert _stock(product_b.id) == 5

    # payload/entidade inválidos
    assert (
        logged_client.put(
            f"/api/tabs/{tab['id']}/items",
            json={"items": "x"},
            headers={"X-CSRFToken": token},
        ).status_code
        == 400
    )
    assert (
        logged_client.put(
            "/api/tabs/999999/items",
            json={"items": []},
            headers={"X-CSRFToken": token},
        ).status_code
        == 404
    )


def test_close_tab_creates_order_without_second_stock_decrement(logged_client):
    """Fechar gera a venda definitiva SEM rebaixar estoque de novo."""

    _open_caixa()
    product = _product("Tab Fechamento", "5.00", 10)
    tab = _open_tab(logged_client, "Mesa 5", product, quantity=4)
    assert _stock(product.id) == 6

    token = _csrf(logged_client)
    response = logged_client.post(
        f"/api/tabs/{tab['id']}/close",
        json={"payments": [{"method_id": _method("Dinheiro").id, "amount": "20.00"}]},
        headers={"X-CSRFToken": token},
    )
    assert response.status_code == 201, response.get_json()
    payload = response.get_json()
    order = payload["order"]
    assert order["total"] == 20.0
    assert order["payments"][0]["name"] == "Dinheiro"
    assert payload["tab"]["status"] == "closed"
    assert payload["tab"]["order_id"] == order["order_id"]
    assert payload["tab"]["closed_by"] == "admin"

    # Nenhuma baixa dupla: estoque permanece o da abertura
    assert _stock(product.id) == 6
    movements = [m for m in _movements(product.id) if m.obs != "Estoque inicial"]
    assert len(movements) == 1
    assert movements[0].movement_type == "saida"

    # recibo do pedido criado funciona pelo fluxo normal do PDV
    receipt = logged_client.get(f"/api/pdv/recibo/{order['order_id']}")
    assert receipt.status_code == 200
    assert receipt.get_json()["order"]["total"] == 20.0

    # some da lista de abertas; detalhe mostra fechada
    open_ids = {t["id"] for t in logged_client.get("/api/tabs").get_json()["tabs"]}
    assert tab["id"] not in open_ids
    detail = logged_client.get(f"/api/tabs/{tab['id']}").get_json()["tab"]
    assert detail["status"] == "closed"

    # fechamento repetido não gera segunda venda
    again = logged_client.post(
        f"/api/tabs/{tab['id']}/close",
        json={"payments": [{"method_id": _method("Dinheiro").id, "amount": "20.00"}]},
        headers={"X-CSRFToken": token},
    )
    assert again.status_code == 400
    assert again.get_json()["error"] == "Comanda já finalizada."

    # comanda fechada não pode ser alterada
    put_again = logged_client.put(
        f"/api/tabs/{tab['id']}/items",
        json={"items": [{"product_id": product.id, "quantity": 1}]},
        headers={"X-CSRFToken": token},
    )
    assert put_again.status_code == 400


def test_close_tab_uses_snapshot_price(logged_client):
    """Preço alterado depois da abertura não muda o total da comanda."""

    _open_caixa()
    product = _product("Tab Snapshot", "10.00", 5)
    tab = _open_tab(logged_client, "Mesa 6", product, quantity=2)
    assert tab["total"] == 20.0

    ProductRepository().update_product(product.id, price=Decimal("15.00"))

    response = logged_client.post(
        f"/api/tabs/{tab['id']}/close",
        json={"payments": [{"method_id": _method("Dinheiro").id, "amount": "20.00"}]},
        headers={"X-CSRFToken": _csrf(logged_client)},
    )
    assert response.status_code == 201, response.get_json()
    order = response.get_json()["order"]
    assert order["total"] == 20.0  # snapshot, não 30.0
    assert order["items"][0]["unit_price"] == 10.0


def test_close_tab_validations(logged_client):
    """Fechamento replica as validações do PDV (caixa, pagamento, fiado)."""

    product = _product("Tab Valida Fech", "8.00", 5)
    token = _csrf(logged_client)

    # sem caixa aberto
    _set_caixa(False)
    tab = _open_tab(logged_client, "Mesa 7", product, quantity=1)
    no_caixa = logged_client.post(
        f"/api/tabs/{tab['id']}/close",
        json={"payments": [{"method_id": _method("Dinheiro").id, "amount": "8.00"}]},
        headers={"X-CSRFToken": token},
    )
    assert no_caixa.status_code == 400
    assert "caixa" in no_caixa.get_json()["error"].lower()

    _open_caixa()

    no_method = logged_client.post(
        f"/api/tabs/{tab['id']}/close", json={}, headers={"X-CSRFToken": token}
    )
    assert no_method.status_code == 400
    assert no_method.get_json()["error"] == "Selecione a forma de pagamento."

    insufficient = logged_client.post(
        f"/api/tabs/{tab['id']}/close",
        json={"payments": [{"method_id": _method("Dinheiro").id, "amount": "5.00"}]},
        headers={"X-CSRFToken": token},
    )
    assert insufficient.status_code == 400
    assert insufficient.get_json()["error"] == "Valores de pagamento insuficientes."

    fiado_without_customer = logged_client.post(
        f"/api/tabs/{tab['id']}/close",
        json={"payments": [{"method_id": _method("Fiado").id, "amount": "8.00"}]},
        headers={"X-CSRFToken": token},
    )
    assert fiado_without_customer.status_code == 400
    assert "cliente" in fiado_without_customer.get_json()["error"].lower()

    # nada disso fechou a comanda
    assert (
        logged_client.get(f"/api/tabs/{tab['id']}").get_json()["tab"]["status"]
        == "open"
    )

    missing = logged_client.post(
        "/api/tabs/999999/close",
        json={"payments": [{"method_id": _method("Dinheiro").id, "amount": "1.00"}]},
        headers={"X-CSRFToken": token},
    )
    assert missing.status_code == 404


def test_close_tab_with_fiado_creates_receivable(logged_client):
    """Fechamento com fiado gera débito no contas a receber."""

    _open_caixa()
    customer_response = logged_client.post(
        "/api/customers",
        json={"name": "Cliente Comanda"},
        headers={"X-CSRFToken": _csrf(logged_client)},
    )
    assert customer_response.status_code == 201
    customer = next(
        c
        for c in customer_response.get_json()["customers"]
        if c["name"] == "Cliente Comanda"
    )

    product = _product("Tab Fiado", "20.00", 3)
    tab = _open_tab(logged_client, "Mesa 8", product, quantity=1)

    response = logged_client.post(
        f"/api/tabs/{tab['id']}/close",
        json={
            "payments": [{"method_id": _method("Fiado").id, "amount": "20.00"}],
            "customer_id": customer["id"],
        },
        headers={"X-CSRFToken": _csrf(logged_client)},
    )
    assert response.status_code == 201, response.get_json()
    order_id = response.get_json()["order"]["order_id"]

    receivables = logged_client.get("/api/receivables").get_json()
    item = next(r for r in receivables["items"] if r["order_id"] == order_id)
    assert item["customer_id"] == customer["id"]
    assert item["balance"] == 20.0

    # fiado não conta no esperado do caixa
    caixa = logged_client.get("/api/caixa").get_json()
    assert str(_method("Fiado").id) not in caixa["system_totals"]


def test_cancel_tab_restores_stock(logged_client):
    """Cancelar devolve o estoque, preserva o registro e bloqueia repetição."""

    product = _product("Tab Cancela", "7.00", 10)
    tab = _open_tab(logged_client, "Mesa 9", product, quantity=3)
    assert _stock(product.id) == 7

    token = _csrf(logged_client)
    response = logged_client.post(
        f"/api/tabs/{tab['id']}/cancel", headers={"X-CSRFToken": token}
    )
    assert response.status_code == 200
    canceled = response.get_json()["tab"]
    assert canceled["status"] == "canceled"
    assert canceled["canceled_by"] == "admin"
    assert canceled["canceled_at"]

    assert _stock(product.id) == 10  # devolveu tudo
    movements = _movements(product.id)
    entrada = [m for m in movements if m.movement_type == "entrada"]
    assert entrada and entrada[-1].quantity == 3
    assert "cancelada" in (entrada[-1].obs or "")

    again = logged_client.post(
        f"/api/tabs/{tab['id']}/cancel", headers={"X-CSRFToken": token}
    )
    assert again.status_code == 400

    events = logged_client.get("/api/audit?entity=tab").get_json()["events"]
    assert any(e["action"] == "tab.cancel" for e in events)

    # fechada não pode ser cancelada (já paga)
    _open_caixa()
    closed_tab = _open_tab(logged_client, "Mesa 11", product, quantity=1)
    logged_client.post(
        f"/api/tabs/{closed_tab['id']}/close",
        json={"payments": [{"method_id": _method("Dinheiro").id, "amount": "7.00"}]},
        headers={"X-CSRFToken": token},
    )
    cancel_closed = logged_client.post(
        f"/api/tabs/{closed_tab['id']}/cancel", headers={"X-CSRFToken": token}
    )
    assert cancel_closed.status_code == 400


def test_register_print_counts_reprints(logged_client):
    """POST /tabs/<id>/print acumula o contador de impressões."""

    product = _product("Tab Impressao", "1.00", 2)
    tab = _open_tab(logged_client, "Mesa 12", product, quantity=1)
    token = _csrf(logged_client)

    first = logged_client.post(
        f"/api/tabs/{tab['id']}/print", headers={"X-CSRFToken": token}
    )
    assert first.status_code == 200
    assert first.get_json()["tab"]["print_count"] == 1

    second = logged_client.post(
        f"/api/tabs/{tab['id']}/print", headers={"X-CSRFToken": token}
    )
    assert second.get_json()["tab"]["print_count"] == 2

    missing = logged_client.post(
        "/api/tabs/999999/print", headers={"X-CSRFToken": token}
    )
    assert missing.status_code == 404


def test_caixa_payload_lists_open_tabs(logged_client):
    """/api/caixa traz as comandas abertas (aviso ao abrir/fechar o caixa)."""

    _open_caixa()
    product = _product("Produto aviso", price="5.00", stock=10)
    tab = _open_tab(logged_client, "Mesa aviso", product, quantity=1)

    payload = logged_client.get("/api/caixa").get_json()
    assert tab["id"] in [t["id"] for t in payload["open_tabs"]]

    token = _csrf(logged_client)
    logged_client.post(
        f"/api/tabs/{tab['id']}/cancel", json={}, headers={"X-CSRFToken": token}
    )
    after = logged_client.get("/api/caixa").get_json()
    assert tab["id"] not in [t["id"] for t in after["open_tabs"]]
