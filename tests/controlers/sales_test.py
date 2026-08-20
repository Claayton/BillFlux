"""Tests from the daily sales routes"""

import json
import re
from datetime import date
from decimal import Decimal

from billflux.infra.repository.order_repository import OrderRepository
from billflux.infra.repository.payment_method_repository import PaymentMethodRepository
from billflux.infra.repository.product_repository import ProductRepository
from billflux.infra.repository.sale_repository import SaleRepository


def _get_csrf_token(client):
    """Fetch the CSRF token from the sales page form."""
    response = client.get("/sales")
    match = re.search(
        r'name="csrf_token" value="([^"]+)"', response.get_data(as_text=True)
    )
    assert match, "CSRF token not found in /sales page"
    return match.group(1)


def test_sales_page(logged_client):
    """GET /sales should render the page with the launch form."""

    response = logged_client.get("/sales")

    assert response.status_code == 200
    page = response.get_data(as_text=True)
    assert "Lançar venda avulsa" in page
    assert "Apenas valor, sem produtos." in page
    assert 'id="sale_total"' in page


def test_sales_metrics_have_filters_and_are_masked(logged_client):
    """Métricas: filtros de período presentes e valores ocultos por padrão."""

    response = logged_client.get("/sales")
    assert response.status_code == 200
    page = response.get_data(as_text=True)

    for label in ["Hoje", "7 dias", "Este mês", "Mês passado"]:
        assert label in page

    assert 'id="period-filter"' in page
    assert 'id="toggle-values"' in page
    assert "Total vendido" in page
    assert "data-periods=" in page
    assert "R$ ••••" in page


def test_sales_requires_login(client):
    """Unauthenticated users should be redirected to login."""

    response = client.get("/sales")

    assert response.status_code == 302
    assert "/login" in response.headers["Location"]


def test_launch_sale(logged_client):
    """POSTing a valid sale should persist it."""

    token = _get_csrf_token(logged_client)
    response = logged_client.post(
        "/sales",
        data={
            "csrf_token": token,
            "date": "2026-01-15",
            "total": "1.250,75",
            "obs": "Feira",
        },
        follow_redirects=True,
    )

    assert response.status_code == 200
    sale = SaleRepository().get_sale_by_date(date(2026, 1, 15))
    assert sale is not None
    assert sale.total == Decimal("1250.75")
    assert sale.obs == "Feira"


def test_launch_sale_same_date_updates(logged_client):
    """POSTing again on the same date should update the total."""

    token = _get_csrf_token(logged_client)
    logged_client.post(
        "/sales",
        data={"csrf_token": token, "date": "2026-01-20", "total": "100,00"},
        follow_redirects=True,
    )
    logged_client.post(
        "/sales",
        data={"csrf_token": token, "date": "2026-01-20", "total": "250,00"},
        follow_redirects=True,
    )

    sale = SaleRepository().get_sale_by_date(date(2026, 1, 20))
    assert sale.total == Decimal("250.00")


def test_launch_sale_invalid(logged_client):
    """POSTing without required fields should not persist anything."""

    token = _get_csrf_token(logged_client)
    logged_client.post(
        "/sales",
        data={"csrf_token": token, "date": "", "total": ""},
        follow_redirects=True,
    )
    logged_client.post(
        "/sales",
        data={"csrf_token": token, "date": "2026-01-25", "total": "0"},
        follow_redirects=True,
    )

    assert SaleRepository().get_sale_by_date(date(2026, 1, 25)) is None


def test_delete_sale(logged_client):
    """Deleting a daily sale should remove it."""

    sale = SaleRepository().insert_sale(date(2026, 1, 30), Decimal("900.00"))
    token = _get_csrf_token(logged_client)

    response = logged_client.post(
        f"/sales/delete/{sale.id}",
        headers={"X-CSRFToken": token},
        follow_redirects=True,
    )

    assert response.status_code == 200
    assert SaleRepository().get_sale(sale.id) is None


def test_sales_get_hx_returns_region(logged_client):
    """Com HX-Request, /sales deve devolver apenas o fragmento da região."""

    response = logged_client.get("/sales", headers={"HX-Request": "true"})

    assert response.status_code == 200
    page = response.get_data(as_text=True)
    assert 'id="sales-region"' in page
    assert 'class="sidebar"' not in page
    assert 'class="site-header"' not in page
    assert "Lançar venda avulsa" in page


def test_sales_post_hx_persists_and_returns_region(logged_client):
    """Lançar venda via HTMX persiste e devolve o fragmento atualizado."""

    token = _get_csrf_token(logged_client)

    response = logged_client.post(
        "/sales",
        data={"csrf_token": token, "date": "2026-03-10", "total": "50,00", "obs": "HX"},
        headers={"HX-Request": "true"},
    )

    assert response.status_code == 200
    page = response.get_data(as_text=True)
    assert 'id="sales-region"' in page
    assert "R$ 50,00" in page
    sale = SaleRepository().get_sale_by_date(date(2026, 3, 10))
    assert sale is not None
    assert sale.total == Decimal("50.00")


def test_sales_delete_hx_returns_region(logged_client):
    """Excluir via HTMX remove a venda e devolve o fragmento."""

    sale = SaleRepository().insert_sale(date(2026, 3, 15), Decimal("100.00"))
    token = _get_csrf_token(logged_client)

    response = logged_client.post(
        f"/sales/delete/{sale.id}",
        data={},
        headers={"X-CSRFToken": token, "HX-Request": "true"},
    )

    assert response.status_code == 200
    assert 'id="sales-region"' in response.get_data(as_text=True)
    assert SaleRepository().get_sale(sale.id) is None


def test_sales_page_includes_pdv_orders(logged_client):
    """PDV orders should feed the daily total shown on the sales page."""

    product = ProductRepository().insert_product(
        name="PDV Resumo Teste", price=Decimal("10.00"), stock_quantity=5
    )
    method = PaymentMethodRepository().get_active_methods()[0]
    OrderRepository().create_order([(product.id, 2)], method.id)

    today_total = sum(
        sale.total for sale in SaleRepository().get_sales() if sale.date == date.today()
    ) + sum(order.total for order in OrderRepository().get_orders_by_date(date.today()))

    response = logged_client.get("/sales")
    assert response.status_code == 200
    page = response.get_data(as_text=True)
    assert "Pedidos de hoje (PDV)" not in page
    assert "source-badge-pdv" in page
    match = re.search(r"data-periods='([^']+)'", page)
    assert match, "data-periods not found"
    periods = json.loads(match.group(1))
    assert periods["hoje"]["total"] == str(today_total)


def test_sales_table_lists_manual_and_pdv_sales(logged_client):
    """A tabela de Vendas deve mostrar vendas avulsas e pedidos do PDV."""

    SaleRepository().insert_sale(date(2026, 2, 10), Decimal("250.00"), obs="Balcão")
    product = ProductRepository().insert_product(
        name="PDV Tabela Teste", price=Decimal("10.00"), stock_quantity=5
    )
    method = PaymentMethodRepository().get_active_methods()[0]
    OrderRepository().create_order([(product.id, 1)], method.id)

    response = logged_client.get("/sales")
    assert response.status_code == 200
    page = response.get_data(as_text=True)
    assert ">Vendas</h2>" in page
    assert "source-badge-manual" in page
    assert "source-badge-pdv" in page
    assert "Balcão" in page
