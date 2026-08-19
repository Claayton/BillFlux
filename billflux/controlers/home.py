"""Module to instantiate the blueprint for the home page"""

from datetime import date

from flask import session
from flask.blueprints import Blueprint
from flask.templating import render_template

from billflux.controlers.bills import _build_stats
from billflux.controlers.sales import _build_summary
from billflux.infra.repository.bill_repository import BillRepository
from billflux.infra.repository.order_repository import OrderRepository
from billflux.infra.repository.sale_repository import SaleRepository

bp = Blueprint("bp_home", __name__)


@bp.route("/home/")
@bp.route("/home")
@bp.route("/")
def index():
    context = {"active": "overview"}

    if session.get("user"):
        today = date.today()
        sales = SaleRepository().get_sales()
        orders = OrderRepository().get_orders()
        bills = BillRepository().get_bills()
        context["sales_summary"] = _build_summary(sales, orders, today)
        context["stats"] = _build_stats(bills, today)
        context["today"] = today
        context["open_bills"] = [
            bill
            for bill in sorted(
                [b for b in bills if not b.status and b.due_date],
                key=lambda b: b.due_date,
            )
        ][:5]
        context["recent_sales"] = _build_recent_movement(sales, orders)

    return render_template("home.html", **context)


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
