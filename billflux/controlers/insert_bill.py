"""File to instantiate the blueprint for the insert bill"""

from datetime import datetime
from decimal import Decimal, InvalidOperation

from flask import flash, redirect, request, url_for
from flask.blueprints import Blueprint

from billflux.infra.repository.bill_repository import BillRepository

bp = Blueprint("bp_insert_bill", __name__)


@bp.route("/insert_bill/", methods=["POST"])
@bp.route("/insert_bill", methods=["POST"])
def insert_bill():
    """Insert a new bill into the database route"""

    bar_code = request.form.get("bar_code")
    value = request.form.get("value")
    vencimento = request.form.get("vencimento")
    reference = request.form.get("reference")
    suplyer = request.form.get("suplyer")
    bill_type = request.form.get("bill_type")
    obs = request.form.get("obs")

    if not value or not vencimento:
        flash("Valor e vencimento são obrigatórios.", "error")
        return redirect(url_for("bp_bills.bills"))

    try:
        formated_value = Decimal(value.replace(",", "."))
        formated_vencimento = datetime.strptime(vencimento, "%Y-%m-%d")
        formated_bar_code = int(bar_code) if bar_code else None
    except (InvalidOperation, ValueError):
        flash("Valor, vencimento ou código de barras inválidos.", "error")
        return redirect(url_for("bp_bills.bills"))

    bill_repository = BillRepository()
    bill_repository.insert_bill(
        bar_code=formated_bar_code,
        value=formated_value,
        due_date=formated_vencimento,
        reference=reference,
        suplyer=suplyer,
        bill_type=bill_type,
        obs=obs,
    )

    flash("Conta cadastrada com sucesso!", "success")
    return redirect(url_for("bp_bills.bills"))
