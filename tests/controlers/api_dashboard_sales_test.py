"""Tests for the dashboard and sales JSON API (SPA)."""

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


def test_dashboard_requires_login(client):
    """Sem sessão, /api/dashboard deve devolver 401 JSON."""

    response = client.get("/api/dashboard")

    assert response.status_code == 401
    assert response.get_json()["error"]


def test_dashboard_returns_metrics(logged_client):
    """Dashboard devolve métricas, série, contas e movimento recente."""

    response = logged_client.get("/api/dashboard")

    assert response.status_code == 200
    data = response.get_json()
    assert set(data["metrics"]) == {"faturamento", "vendas", "ticket", "lucro"}
    assert data["period"]["key"] == "7d"  # período padrão
    assert isinstance(data["series"], list)
    assert isinstance(data["open_bills"], list)
    assert isinstance(data["recent_sales"], list)


def test_dashboard_accounts_pdv_profit(logged_client):
    """Lucro bruto reflete pedidos PDV (preço − custo) × qtd no período."""

    product = ProductRepository().insert_product(
        name="API Dashboard",
        price=Decimal("10.00"),
        cost=Decimal("4.00"),
        stock_quantity=5,
    )
    method = PaymentMethodRepository().get_active_methods()[0]
    OrderRepository().create_order([(product.id, 2)], method.id)

    response = logged_client.get("/api/dashboard?periodo=hoje")

    assert response.status_code == 200
    data = response.get_json()
    assert data["metrics"]["faturamento"] == 20.0
    assert data["metrics"]["lucro"] == 12.0  # (10 - 4) * 2


def test_dashboard_specific_date(logged_client):
    """?date=YYYY-MM-DD filtra o período para o dia exato."""

    response = logged_client.get("/api/dashboard?date=2026-01-05")

    assert response.status_code == 200
    data = response.get_json()
    assert data["period"]["key"] == "dia"
    assert data["period"]["start"] == "2026-01-05"


def test_sales_requires_login(client):
    """Sem sessão, /api/sales deve devolver 401 JSON."""

    assert client.get("/api/sales").status_code == 401


def test_sales_list_combines_manual_and_pdv(logged_client):
    """Lista junta lançamentos manuais e pedidos do PDV."""

    product = ProductRepository().insert_product(
        name="API Sales", price=Decimal("7.00"), stock_quantity=5
    )
    method = PaymentMethodRepository().get_active_methods()[0]
    OrderRepository().create_order([(product.id, 1)], method.id)
    SaleRepository().insert_sale(
        __import__("datetime").date(2026, 8, 18), Decimal("813.45")
    )

    response = logged_client.get("/api/sales")

    assert response.status_code == 200
    data = response.get_json()
    kinds = {sale["kind"] for sale in data["sales"]}
    assert "manual" in kinds
    assert "pdv" in kinds
    assert set(data["periods"]) == {"hoje", "7d", "mes", "mes_anterior"}


def test_sales_create_and_upsert(logged_client):
    """POST cria/atualiza a venda avulsa da data (upsert)."""

    token = _csrf(logged_client)
    response = logged_client.post(
        "/api/sales",
        json={"date": "2026-07-01", "total": "150,50", "obs": "Feira"},
        headers={"X-CSRFToken": token},
    )

    assert response.status_code == 201
    data = response.get_json()
    sale = next(s for s in data["sales"] if s["date"] == "2026-07-01")
    assert sale["total"] == 150.5
    assert sale["obs"] == "Feira"

    response = logged_client.post(
        "/api/sales",
        json={"date": "2026-07-01", "total": "160,00", "obs": ""},
        headers={"X-CSRFToken": token},
    )
    assert response.status_code == 201
    data = response.get_json()
    updated = [s for s in data["sales"] if s["date"] == "2026-07-01"]
    assert len(updated) == 1  # upsert: continua uma venda por data
    assert updated[0]["total"] == 160.0


def test_sales_create_validation(logged_client):
    """POST sem data/total ou com valor inválido deve devolver 400."""

    token = _csrf(logged_client)
    missing = logged_client.post(
        "/api/sales", json={"date": "", "total": ""}, headers={"X-CSRFToken": token}
    )
    assert missing.status_code == 400

    invalid = logged_client.post(
        "/api/sales",
        json={"date": "nao-data", "total": "abc"},
        headers={"X-CSRFToken": token},
    )
    assert invalid.status_code == 400

    zero = logged_client.post(
        "/api/sales",
        json={"date": "2026-07-02", "total": "0"},
        headers={"X-CSRFToken": token},
    )
    assert zero.status_code == 400


def test_sales_delete(logged_client):
    """DELETE remove uma venda avulsa e devolve a lista atualizada."""

    token = _csrf(logged_client)
    created = logged_client.post(
        "/api/sales",
        json={"date": "2026-07-03", "total": "50,00"},
        headers={"X-CSRFToken": token},
    ).get_json()
    sale_id = next(s["id"] for s in created["sales"] if s["date"] == "2026-07-03")

    response = logged_client.delete(
        f"/api/sales/{sale_id}", headers={"X-CSRFToken": token}
    )

    assert response.status_code == 200
    data = response.get_json()
    assert not any(s["id"] == sale_id for s in data["sales"])

    missing = logged_client.delete("/api/sales/999999", headers={"X-CSRFToken": token})
    assert missing.status_code == 404
