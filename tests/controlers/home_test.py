"""Tests from home routes"""

from datetime import date
from decimal import Decimal

from billflux.infra.repository.order_repository import OrderRepository
from billflux.infra.repository.payment_method_repository import (
    PaymentMethodRepository,
)
from billflux.infra.repository.product_repository import ProductRepository
from billflux.infra.repository.sale_repository import SaleRepository


def test_home_route_1(client):
    """Testing the / rote"""

    url = """/"""

    response = client.get(url)

    assert response.status_code == 200


def test_home_rotue_2(client):
    """Testing the /home route"""

    url = """/home"""

    response = client.get(url)

    assert response.status_code == 200


def test_home_rotue_3(client):
    """Testing the /home/ route"""

    url = """/home/"""

    response = client.get(url)

    assert response.status_code == 200


def test_root_redirects_logged_user_to_sales(logged_client):
    """Logged-in users hitting / should land on the SPA (client-side redirect)."""

    response = logged_client.get("/")

    assert response.status_code == 200
    page = response.get_data(as_text=True)
    assert '<div id="app">' in page


def test_home_dashboard_logged_in(logged_client):
    """Logged-in users should see the dashboard instead of the hero."""

    response = logged_client.get("/home")

    assert response.status_code == 200
    page = response.get_data(as_text=True)
    assert "Visão geral" in page
    assert "Faturamento" in page
    assert "Nº de vendas" in page
    assert "Ticket médio" in page
    assert "Lucro bruto" in page
    assert "Vendas por dia" in page
    assert "Contas em aberto" in page
    assert "Últimos 7 dias" in page  # período padrão do dashboard
    assert 'class="hero"' not in page


def test_home_dashboard_shows_pdv_movement(logged_client):
    """PDV orders should appear in the recent movement list."""

    product = ProductRepository().insert_product(
        name="PDV Home Teste", price=Decimal("5.00"), stock_quantity=5
    )
    method = PaymentMethodRepository().get_active_methods()[0]
    OrderRepository().create_order([(product.id, 1)], method.id)

    response = logged_client.get("/home")

    assert response.status_code == 200
    assert "PDV" in response.get_data(as_text=True)


def _brl(value):
    return f"R$ {value:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")


def _today_metrics():
    """Espelha o cálculo do dashboard para 'hoje', lendo o banco de teste."""
    sales = SaleRepository().get_sales()
    orders = OrderRepository().get_orders()
    total = Decimal("0")
    count = 0
    for sale in sales:
        if sale.date == date.today():
            total += sale.total
            count += 1
    for order in orders:
        if order.created_at.date() == date.today():
            total += order.total
            count += 1
    ticket = total / count if count else Decimal("0")

    cost_map = {p.id: p.cost for p in ProductRepository().get_products()}
    profit = Decimal("0")
    for order in orders:
        if order.created_at.date() != date.today():
            continue
        for item in OrderRepository().get_order_items(order.id):
            cost = cost_map.get(item.product_id, Decimal("0"))
            profit += (item.unit_price - cost) * item.quantity
    return total, count, ticket, profit


def test_dashboard_metrics_with_data(logged_client):
    """Faturamento, vendas, ticket médio e lucro devem refletir os dados."""

    product = ProductRepository().insert_product(
        name="Custo Dashboard",
        price=Decimal("10.00"),
        cost=Decimal("4.00"),
        stock_quantity=5,
    )
    method = PaymentMethodRepository().get_active_methods()[0]
    OrderRepository().create_order([(product.id, 1)], method.id)
    SaleRepository().insert_sale(date.today(), Decimal("30.00"))

    response = logged_client.get("/home?periodo=hoje")

    assert response.status_code == 200
    page = response.get_data(as_text=True)
    total, count, ticket, profit = _today_metrics()
    assert _brl(total) in page  # faturamento
    assert _brl(ticket) in page  # ticket médio
    assert _brl(profit) in page  # lucro bruto


def test_dashboard_manual_sale_has_no_profit(logged_client):
    """Venda avulsa não contribui com lucro bruto (isola por data)."""

    past = date(2025, 11, 11)
    SaleRepository().insert_sale(past, Decimal("50.00"))

    response = logged_client.get(f"/home?date={past:%Y-%m-%d}")

    assert response.status_code == 200
    page = response.get_data(as_text=True)
    assert "R$ 50,00" in page  # faturamento
    assert "R$ 0,00" in page  # lucro bruto de venda avulsa é 0


def test_dashboard_period_filter(logged_client):
    """O filtro ?periodo= deve ser aceito e renderizar o período."""

    response = logged_client.get("/home?periodo=30d")

    assert response.status_code == 200
    page = response.get_data(as_text=True)
    assert "Últimos 30 dias" in page


def test_dashboard_specific_date(logged_client):
    """?date=YYYY-MM-DD filtra por um dia específico."""

    SaleRepository().insert_sale(date(2026, 1, 5), Decimal("100.00"))

    response = logged_client.get("/home?date=2026-01-05")

    assert response.status_code == 200
    page = response.get_data(as_text=True)
    assert "R$ 100,00" in page
    assert 'value="2026-01-05"' in page


def test_dashboard_empty_period_shows_empty_chart(logged_client):
    """Um período sem vendas deve mostrar o estado vazio do gráfico."""

    response = logged_client.get("/home?date=2020-01-01")

    assert response.status_code == 200
    page = response.get_data(as_text=True)
    assert "Nenhuma venda neste período." in page
    assert 'class="chart-bars"' not in page


def test_dashboard_hx_returns_region(logged_client):
    """Com HX-Request, /home deve devolver apenas o fragmento do dashboard."""

    response = logged_client.get("/home", headers={"HX-Request": "true"})

    assert response.status_code == 200
    page = response.get_data(as_text=True)
    assert 'id="dashboard-region"' in page
    assert 'class="hero"' not in page


def test_sidebar_order(logged_client):
    """Visão geral deve aparecer por último na sidebar."""

    response = logged_client.get("/home")
    page = response.get_data(as_text=True)

    sidebar = page.split('<aside class="sidebar">')[1].split("</aside>")[0]
    assert sidebar.find('href="/home"') > sidebar.find('href="/accounts"')
    assert sidebar.find('href="/home"') > sidebar.find('href="/products"')
