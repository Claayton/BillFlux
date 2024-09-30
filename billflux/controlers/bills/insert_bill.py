"""File to instantiate the blueprint for the insert bill"""

from datetime import datetime
from flask import request, redirect, url_for
from flask.blueprints import Blueprint
from flask_login import current_user
from billflux.infra.repository.bills_repository import BillRepository
from billflux.config import settings


bp = Blueprint("bp_insert_bill", __name__)

database_url = settings["development"].DATABASE_URL


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

    bill_repository = BillRepository(database_url)
    bill_repository.insert_bill(
        bar_code=bar_code,
        value=value,
        due_date=formated_vencimento,
        reference=reference,
        suplyer=suplyer,
        bill_type=bill_type,
        obs=obs,
        user_id=current_user.id,
    )

    return redirect(url_for("bp_get_bills.bills"), code=201)
