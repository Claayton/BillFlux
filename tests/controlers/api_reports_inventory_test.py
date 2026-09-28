"""Tests for stock reports and inventory count JSON APIs."""

from decimal import Decimal

from billflux.infra.repository.product_repository import ProductRepository


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


def test_reports_require_login(client):
    """Relatórios exigem sessão autenticada."""
    assert client.get("/api/reports/movements").status_code == 401
    assert client.get("/api/reports/low-stock").status_code == 401
    token = _csrf(client)
    assert (
        client.post(
            "/api/inventory/count",
            json={},
            headers={"X-CSRFToken": token},
        ).status_code
        == 401
    )


def test_reports_movements_filters(client):
    """Movimentações suportam filtro por produto/tipo e validam parâmetros."""

    assert _login(client).status_code == 200
    product = ProductRepository().insert_product(
        name="Rel Mov", price=Decimal("5.00"), stock_quantity=10
    )
    ProductRepository().adjust_stock(product_id=product.id, delta=5, obs="reposição")
    other = ProductRepository().insert_product(
        name="Rel Mov Outro", price=Decimal("2.00"), stock_quantity=3
    )

    token = _csrf(client)
    all_rows = client.get("/api/reports/movements").get_json()
    assert all_rows["total"] >= 2

    by_product = client.get(
        f"/api/reports/movements?product_id={product.id}"
    ).get_json()
    assert by_product["total"] == 2
    names = {m["product_name"] for m in by_product["movements"]}
    assert names == {"Rel Mov"}
    types = {m["movement_type"] for m in by_product["movements"]}
    assert types == {"entrada", "ajuste"}

    by_type = client.get(
        f"/api/reports/movements?product_id={product.id}&type=ajuste"
    ).get_json()
    assert by_type["total"] == 1
    assert by_type["movements"][0]["quantity"] == 5
    assert by_type["movements"][0]["obs"] == "reposição"

    assert (
        client.get(
            f"/api/reports/movements?product_id={other.id}&type=ajuste"
        ).get_json()["total"]
        == 0
    )

    invalid = client.get("/api/reports/movements?type=qualquer")
    assert invalid.status_code == 400
    bad_date = client.get("/api/reports/movements?date_from=31/12/2025")
    assert bad_date.status_code == 400
    bad_period = client.get(
        "/api/reports/movements?date_from=2026-01-10&date_to=2026-01-01"
    )
    assert bad_period.status_code == 400
    assert token  # csrf disponível


def test_reports_low_stock(client):
    """Lista produtos abaixo do mínimo definido ou com estoque negativo.

    Produtos sem mínimo configurado e zerados (ainda sem controle de
    estoque) não entram na lista."""

    assert _login(client).status_code == 200
    repository = ProductRepository()
    low = repository.insert_product(
        name="Rel Baixo", price=Decimal("1.00"), stock_quantity=2, min_stock=5
    )
    zero_controlled = repository.insert_product(
        name="Rel Zerado Min", price=Decimal("1.00"), stock_quantity=0, min_stock=6
    )
    uncontrolled = repository.insert_product(
        name="Rel Sem Controle", price=Decimal("1.00"), stock_quantity=0, min_stock=0
    )
    negative = repository.insert_product(
        name="Rel Negativo", price=Decimal("1.00"), stock_quantity=-2, min_stock=0
    )
    ok = repository.insert_product(
        name="Rel Ok", price=Decimal("1.00"), stock_quantity=10, min_stock=2
    )
    inactive = repository.insert_product(
        name="Rel Inativo",
        price=Decimal("1.00"),
        stock_quantity=0,
        min_stock=5,
        active=False,
    )

    data = client.get("/api/reports/low-stock").get_json()
    ids = [p["id"] for p in data["products"]]
    assert low.id in ids
    assert zero_controlled.id in ids
    assert negative.id in ids
    assert uncontrolled.id not in ids
    assert ok.id not in ids
    assert inactive.id not in ids

    low_item = next(p for p in data["products"] if p["id"] == low.id)
    assert low_item["stock_quantity"] == 2
    assert low_item["min_stock"] == 5
    assert low_item["deficit"] == 3
    assert low_item["out_of_stock"] is False

    zero_item = next(p for p in data["products"] if p["id"] == zero_controlled.id)
    assert zero_item["out_of_stock"] is True
    assert data["count"] == len(data["products"])


def test_inventory_count_adjusts_stock(client):
    """Contagem ajusta estoque, gera movimento 'ajuste' e audita."""

    assert _login(client).status_code == 200
    product = ProductRepository().insert_product(
        name="Inventário", price=Decimal("3.00"), stock_quantity=5
    )
    token = _csrf(client)

    response = client.post(
        "/api/inventory/count",
        json={"items": [{"product_id": product.id, "counted": 8}]},
        headers={"X-CSRFToken": token},
    )
    assert response.status_code == 200
    data = response.get_json()
    assert data["counted"] == 1
    assert data["adjusted"] == 1
    assert data["changes"][0]["before"] == 5
    assert data["changes"][0]["after"] == 8
    assert data["changes"][0]["delta"] == 3
    assert ProductRepository().get_product(product.id).stock_quantity == 8

    movements = client.get(f"/api/products/{product.id}/movements").get_json()[
        "movements"
    ]
    ajuste = next(m for m in movements if m["movement_type"] == "ajuste")
    assert ajuste["quantity"] == 3
    assert "Inventário" in ajuste["obs"]

    events = client.get("/api/audit?entity=product").get_json()["events"]
    assert any(e["action"] == "inventory.count" for e in events)

    # repetir a mesma contagem não gera ajuste
    same = client.post(
        "/api/inventory/count",
        json={"items": [{"product_id": product.id, "counted": 8}]},
        headers={"X-CSRFToken": token},
    )
    assert same.get_json()["adjusted"] == 0
    assert ProductRepository().get_product(product.id).stock_quantity == 8

    # produto repetido no payload: a última contagem vence
    dup = client.post(
        "/api/inventory/count",
        json={
            "items": [
                {"product_id": product.id, "counted": 3},
                {"product_id": product.id, "counted": 4},
            ],
            "obs": "Contagem noturna",
        },
        headers={"X-CSRFToken": token},
    )
    assert dup.status_code == 200
    assert dup.get_json()["adjusted"] == 1
    assert dup.get_json()["changes"][0]["before"] == 8
    assert dup.get_json()["changes"][0]["after"] == 4
    assert ProductRepository().get_product(product.id).stock_quantity == 4


def test_inventory_count_validation(client):
    """Contagem valida itens, quantidade negativa e produto inexistente."""

    assert _login(client).status_code == 200
    token = _csrf(client)

    empty = client.post(
        "/api/inventory/count", json={"items": []}, headers={"X-CSRFToken": token}
    )
    assert empty.status_code == 400

    negative = client.post(
        "/api/inventory/count",
        json={"items": [{"product_id": 1, "counted": -2}]},
        headers={"X-CSRFToken": token},
    )
    assert negative.status_code == 400

    missing = client.post(
        "/api/inventory/count",
        json={"items": [{"product_id": 999999, "counted": 1}]},
        headers={"X-CSRFToken": token},
    )
    assert missing.status_code == 404
