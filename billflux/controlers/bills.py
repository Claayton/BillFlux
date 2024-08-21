"""Module to instantiate the blueprint for the bills page"""

from flask.blueprints import Blueprint
from flask.templating import render_template
from billflux.infra.repository.bill_repository import BillRepository


bp = Blueprint("bp_bills", __name__)


@bp.route("/bills/", methods=["GET", "POST"])
@bp.route("/bills", methods=["GET", "POST"])
def bills():

    bills_repository = BillRepository()
    bills_list = bills_repository.get_bills()

    return render_template("bills.html", bills_list=bills_list)
