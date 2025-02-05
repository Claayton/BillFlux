"""File to instantiate the blueprint for pay_bill"""

from flask.blueprints import Blueprint
from flask import redirect, url_for
from billflux.infra.repository.bills_repository import BillRepository
from billflux.config import settings


bp = Blueprint("bp_pay_bill", __name__)

database_url = settings["development"].DATABASE_URL


@bp.route("/pay_bill/<int:bill_id>", methods=["GET", "POST"])
def pay_bill(bill_id):
    """Mount bills route, and update a bill to pay"""

    bills_repository = BillRepository(database_url)
    bills_repository.update_bill(bill_id=bill_id, status=True)

    return redirect(url_for("bp_get_bills.bills"))
