"""Tests from the daily sales routes"""

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
    assert "Vendas diárias" in page
    assert "Lançar vendas do dia" in page
    assert "Vendas hoje" in page
    assert 'id="sale_total"' in page


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


def test_sales_page_includes_pdv_orders(logged_client):
    """PDV orders should feed the daily total shown on the sales page."""

    product = ProductRepository().insert_product(
        name="PDV Resumo Teste", price=Decimal("10.00"), stock_quantity=5
    )
    method = PaymentMethodRepository().get_active_methods()[0]
    OrderRepository().create_order([(product.id, 2)], method.id)

    today_total = sum(
        order.total for order in OrderRepository().get_orders_by_date(date.today())
    )

    response = logged_client.get("/sales")
    assert response.status_code == 200
    page = response.get_data(as_text=True)
    assert "Pedidos de hoje (PDV)" in page
    formatted = (
        f"R$ {today_total:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
    )
    assert formatted in page
