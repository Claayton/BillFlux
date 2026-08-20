"""Module to instantiate the blueprint for the home page"""

from datetime import date, datetime, timedelta
from decimal import Decimal

from flask import request, session
from flask.blueprints import Blueprint
from flask.templating import render_template

from billflux.infra.repository.bill_repository import BillRepository
from billflux.infra.repository.order_repository import OrderRepository
from billflux.infra.repository.product_repository import ProductRepository
from billflux.infra.repository.sale_repository import SaleRepository

bp = Blueprint("bp_home", __name__)


@bp.route("/home/")
@bp.route("/home")
def overview():
    """Dashboard de relatórios (faturamento, vendas, ticket, lucro)."""

    if not session.get("user"):
        return render_template("home.html", active="overview")

    context = _dashboard_context(request.args)
    if request.headers.get("HX-Request"):
        return render_template("_dashboard_region.html", **context)
    return render_template("home.html", **context)


def _resolve_period(args):
    """Resolve o período selecionado (hoje, ontem, 7d, 30d, mês passado ou dia)."""
    date_param = args.get("date")
    if date_param:
        try:
            day = datetime.strptime(date_param, "%Y-%m-%d").date()
            return {
                "key": "dia",
                "start": day,
                "end": day,
                "date": date_param,
                "label": day.strftime("%d/%m/%Y"),
            }
        except ValueError:
            pass

    today = date.today()
    period = args.get("periodo", "7d")

    if period == "ontem":
        day = today - timedelta(days=1)
        return {"key": "ontem", "start": day, "end": day, "date": "", "label": "Ontem"}
    if period == "7d":
        return {
            "key": "7d",
            "start": today - timedelta(days=6),
            "end": today,
            "date": "",
            "label": "Últimos 7 dias",
        }
    if period == "30d":
        return {
            "key": "30d",
            "start": today - timedelta(days=29),
            "end": today,
            "date": "",
            "label": "Últimos 30 dias",
        }
    if period == "mes_anterior":
        first = today.replace(day=1)
        end = first - timedelta(days=1)
        start = end.replace(day=1)
        return {
            "key": "mes_anterior",
            "start": start,
            "end": end,
            "date": "",
            "label": "Mês passado",
        }

    return {"key": "hoje", "start": today, "end": today, "date": "", "label": "Hoje"}


def _build_dashboard(sales, orders, start, end):
    """Métricas e série diária de vendas dentro do período (manual + PDV)."""
    total = Decimal("0")
    count = 0
    day_totals = {}

    for sale in sales:
        if start <= sale.date <= end:
            total += sale.total
            count += 1
            day_totals[sale.date] = day_totals.get(sale.date, Decimal("0")) + sale.total

    for order in orders:
        order_date = order.created_at.date()
        if start <= order_date <= end:
            total += order.total
            count += 1
            day_totals[order_date] = (
                day_totals.get(order_date, Decimal("0")) + order.total
            )

    ticket = total / count if count else Decimal("0")

    series = []
    cursor = start
    while cursor <= end:
        value = day_totals.get(cursor, Decimal("0"))
        series.append(
            {"date": cursor, "label": cursor.strftime("%d/%m"), "value": value}
        )
        cursor += timedelta(days=1)

    maximum = max((item["value"] for item in series), default=Decimal("0"))
    for item in series:
        item["percent"] = int(item["value"] / maximum * 100) if maximum else 0

    return {
        "total": total,
        "count": count,
        "ticket": ticket,
        "series": series,
        "maximum": maximum,
    }


def _gross_profit(orders, cost_map):
    """Lucro bruto dos pedidos PDV: soma (preço de venda − custo) × quantidade."""
    profit = Decimal("0")
    repository = OrderRepository()
    for order in orders:
        for item in repository.get_order_items(order.id):
            cost = cost_map.get(item.product_id, Decimal("0"))
            profit += (item.unit_price - cost) * item.quantity
    return profit


def _dashboard_context(args):
    """Constrói o contexto do dashboard para o período selecionado."""
    today = date.today()
    sales = SaleRepository().get_sales()
    orders = OrderRepository().get_orders()
    bills = BillRepository().get_bills()

    period = _resolve_period(args)
    dashboard = _build_dashboard(sales, orders, period["start"], period["end"])

    cost_map = {p.id: p.cost for p in ProductRepository().get_products()}
    in_range_orders = [
        order
        for order in orders
        if period["start"] <= order.created_at.date() <= period["end"]
    ]
    profit = _gross_profit(in_range_orders, cost_map)

    open_bills = [
        bill
        for bill in sorted(
            [b for b in bills if not b.status and b.due_date],
            key=lambda b: b.due_date,
        )
    ][:5]

    return {
        "active": "overview",
        "today": today,
        "period": period,
        "metrics": {
            "faturamento": dashboard["total"],
            "vendas": dashboard["count"],
            "ticket": dashboard["ticket"],
            "lucro": profit,
        },
        "series": dashboard["series"],
        "chart_max": dashboard["maximum"],
        "open_bills": open_bills,
        "recent_sales": _build_recent_movement(sales, orders),
    }


def _build_recent_movement(sales, orders):
    """Junta lançamentos manuais e pedidos do PDV no movimento recente."""

    items = []
    for sale in sales:
        items.append({"date": sale.date, "source": "Manual", "value": sale.total})
    for order in orders:
        items.append(
            {
                "date": order.created_at.date(),
                "source": "PDV",
                "value": order.total,
            }
        )
    return sorted(items, key=lambda item: item["date"], reverse=True)[:5]
