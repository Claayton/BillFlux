"""Module to instantiate the blueprint for the home page"""

from datetime import date

from flask import session
from flask.blueprints import Blueprint
from flask.templating import render_template

from billflux.controlers.sales import _build_summary
from billflux.infra.repository.sale_repository import SaleRepository

bp = Blueprint("bp_home", __name__)


@bp.route("/home/")
@bp.route("/home")
@bp.route("/")
def index():
    context = {"active": "overview"}

    if session.get("user"):
        sales = SaleRepository().get_sales()
        context["sales_summary"] = _build_summary(sales, date.today())

    return render_template("home.html", **context)
