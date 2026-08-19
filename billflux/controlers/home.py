"""Module to instantiate the blueprint for the home page"""

from datetime import date

from flask import session
from flask.blueprints import Blueprint
from flask.templating import render_template

from billflux.controlers.bills import _build_stats
from billflux.controlers.sales import _build_summary
from billflux.infra.repository.bill_repository import BillRepository
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
        bills = BillRepository().get_bills()
        context["sales_summary"] = _build_summary(sales, today)
        context["stats"] = _build_stats(bills, today)
        context["today"] = today
        context["open_bills"] = [
            bill
            for bill in sorted(
                [b for b in bills if not b.status and b.due_date],
                key=lambda b: b.due_date,
            )
        ][:5]
        context["recent_sales"] = sales[:5]

    return render_template("home.html", **context)
