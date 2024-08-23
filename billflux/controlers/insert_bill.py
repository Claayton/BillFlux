"""File to instantiate the blueprint for the insert bill"""

from datetime import datetime
from flask import request, redirect, url_for
from flask.blueprints import Blueprint
from billflux.infra.repository.bill_repository import BillRepository


bp = Blueprint("bp_insert_bill", __name__)


@bp.route("/insert_bill/", methods=["GET", "POST"])
def insert_bill():
    """Insert a new bill into the database route"""

    # Insert a new account and data in main table
    bar_code = request.form.get("car_code")
    value = request.form.get("value")
    vencimento = request.form.get("vencimento")
    reference = request.form.get("reference")
    suplyer = request.form.get("suplyer")
    bill_type = request.form.get("bill_type")
    obs = request.form.get("obs")

    formated_vencimento = datetime.strptime(vencimento, "%Y-%m-%d")

    bill_repository = BillRepository()
    bill_repository.insert_bill(
        bar_code=bar_code,
        value=value,
        due_date=formated_vencimento,
        reference=reference,
        suplyer=suplyer,
        bill_type=bill_type,
        obs=obs,
    )

    return redirect(url_for("bp_bills.bills"))
