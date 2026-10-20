"""Tests for the purchase schedule (sugestões de reposição)."""

from datetime import date
from decimal import Decimal


def _csrf(client):
    response = client.get("/api/auth/csrf")
    assert response.status_code == 200
    return response.get_json()["csrf_token"]


def _dom_weekday(d: date) -> int:
    return (d.weekday() + 1) % 7


def _fixture(order_day):
    """Produto + fornecedor vinculado no dia informado, abaixo do ideal."""
    from billflux.infra.repository.product_repository import ProductRepository
    from billflux.infra.repository.product_supplier_repository import (
        ProductSupplierRepository,
    )
    from billflux.infra.repository.supplier_repository import SupplierRepository

    supplier = SupplierRepository().insert_supplier(name="Distribuidora Teste")
    product = ProductRepository().insert_product(
        name="Gelo 5kg", price=Decimal("30"), cost=Decimal("20"), stock_quantity=1
    )
    # ideal alto e estoque baixo -> entra na sugestão
    ProductRepository().update_product(product.id, ideal_stock=10, min_stock=2)
    ProductSupplierRepository().upsert(
        product_id=product.id,
        supplier_id=supplier.id,
        delivery_day=order_day,
        lead_time=1,
        is_primary=True,
        frequency="semanal",
        week_parity=0,
    )
    return supplier, product


def test_schedule_today_lists_product_due_today(logged_client):
    supplier, product = _fixture(_dom_weekday(date.today()))

    payload = logged_client.get("/api/schedule/today").get_json()
    suppliers = {s["supplier_id"]: s for s in payload["suggestions"]}
    assert supplier.id in suppliers
    names = [p["product_name"] for p in suppliers[supplier.id]["products"]]
    assert "Gelo 5kg" in names
    entry = suppliers[supplier.id]["products"][0]
    assert entry["suggested_qty"] == 9  # ideal 10 - estoque 1
    assert entry["reason"]


def test_schedule_week_matches_day_of_week(logged_client):
    order_day = _dom_weekday(date.today())
    _fixture(order_day)

    week = logged_client.get("/api/schedule/week").get_json()["week"]
    today = next(d for d in week if d["is_today"])
    assert today["day_of_week"] == order_day
    assert any(
        p["product_name"] == "Gelo 5kg"
        for s in today["suggestions"]
        for p in s["products"]
    )


def test_schedule_ignores_wrong_day(logged_client):
    # Vincula num dia diferente de hoje -> não deve aparecer.
    other_day = (_dom_weekday(date.today()) + 3) % 7
    supplier, _product = _fixture(other_day)

    payload = logged_client.get("/api/schedule/today").get_json()
    assert all(s["supplier_id"] != supplier.id for s in payload["suggestions"])


def _make_supplier(name="Dist X"):
    from billflux.infra.repository.supplier_repository import SupplierRepository

    return SupplierRepository().insert_supplier(name=name)


def _make_product(name="Gelo 5kg", ideal=10, stock=1):
    from billflux.infra.repository.product_repository import ProductRepository

    p = ProductRepository().insert_product(
        name=name, price=Decimal("30"), cost=Decimal("20"), stock_quantity=stock
    )
    ProductRepository().update_product(p.id, ideal_stock=ideal, min_stock=1)
    return p


def test_link_multiple_days_appears_in_each_day(logged_client):
    """Vínculo com Seg/Qua/Sex aparece nas 3 colunas da agenda, sem duplicar."""
    token = _csrf(logged_client)
    supplier = _make_supplier()
    product = _make_product()

    resp = logged_client.post(
        f"/api/products/{product.id}/suppliers",
        json={"supplier_id": supplier.id, "delivery_days": [1, 3, 5]},
        headers={"X-CSRFToken": token},
    )
    assert resp.status_code == 201, resp.get_json()
    assert resp.get_json()["link"]["delivery_days"] == [1, 3, 5]

    week = logged_client.get("/api/schedule/week").get_json()["week"]
    by_dow = {d["day_of_week"]: d for d in week}

    for dow in (1, 3, 5):
        matches = [
            p
            for s in by_dow[dow]["suggestions"]
            for p in s["products"]
            if p["product_name"] == "Gelo 5kg"
        ]
        assert len(matches) == 1, f"deveria aparecer 1x no dia {dow}"
    for dow in (0, 2, 4, 6):
        assert not any(
            p["product_name"] == "Gelo 5kg"
            for s in by_dow[dow]["suggestions"]
            for p in s["products"]
        )


def test_link_requires_at_least_one_day(logged_client):
    token = _csrf(logged_client)
    supplier = _make_supplier("S2")
    product = _make_product("P2")
    resp = logged_client.post(
        f"/api/products/{product.id}/suppliers",
        json={"supplier_id": supplier.id},
        headers={"X-CSRFToken": token},
    )
    assert resp.status_code == 400


def test_link_requires_ideal_stock(logged_client):
    token = _csrf(logged_client)
    from billflux.infra.repository.product_repository import ProductRepository

    supplier = _make_supplier("S3")
    product = ProductRepository().insert_product(
        name="Sem ideal", price=Decimal("10"), stock_quantity=1
    )
    resp = logged_client.post(
        f"/api/products/{product.id}/suppliers",
        json={"supplier_id": supplier.id, "delivery_days": [2]},
        headers={"X-CSRFToken": token},
    )
    assert resp.status_code == 400
