"""File to instantiate the blueprint for the insert bill"""

import re
from datetime import datetime
from decimal import Decimal, InvalidOperation

from flask import flash, redirect, request, url_for
from flask.blueprints import Blueprint

from billflux.controlers.auth import login_required
from billflux.infra.repository.account_repository import AccountRepository
from billflux.infra.repository.bill_repository import BillRepository
from billflux.services.barcode import (
    decode_barcode,
    is_vencimento_autofillable,
)

bp = Blueprint("bp_insert_bill", __name__)


@bp.route("/insert_bill/", methods=["POST"])
@bp.route("/insert_bill", methods=["POST"])
@login_required
def insert_bill():
    """Insert a new bill into the database route"""

    bar_code = (request.form.get("bar_code") or "").strip()
    value = request.form.get("value")
    vencimento = request.form.get("vencimento")
    reference = request.form.get("reference")
    suplyer = request.form.get("suplyer")
    bill_type = request.form.get("bill_type")
    account_id = request.form.get("account_id")
    pix_key = (request.form.get("pix_key") or "").strip()
    pix_payload = (request.form.get("pix_payload") or "").strip()
    pix_image = (request.form.get("pix_image") or "").strip()
    obs = request.form.get("obs")

    decoded = None
    if bar_code:
        decoded = decode_barcode(bar_code)
        if decoded:
            if not value and decoded["value"] is not None:
                value = str(decoded["value"])
            if not vencimento and is_vencimento_autofillable(decoded["vencimento"]):
                vencimento = decoded["vencimento"].isoformat()

    if not value or not vencimento:
        if bar_code and decoded is None:
            flash("Código de barras inválido. Verifique o número digitado.", "error")
        elif bar_code and not vencimento:
            flash(
                "Não foi possível identificar o vencimento (data muito antiga no "
                "código). Preencha a data manualmente.",
                "error",
            )
        elif bar_code and not value:
            flash("Não foi possível identificar o valor no código de barras.", "error")
        else:
            flash("Valor e vencimento são obrigatórios.", "error")
        return redirect(url_for("bp_bills.bills"))

    try:
        formated_value = Decimal(value.replace(",", "."))
        formated_vencimento = datetime.strptime(vencimento, "%Y-%m-%d")
        formated_bar_code = re.sub(r"\D", "", bar_code) if bar_code else None
        formated_account_id = int(account_id) if account_id else None
    except (InvalidOperation, ValueError):
        flash("Valor, vencimento ou código de barras inválidos.", "error")
        return redirect(url_for("bp_bills.bills"))

    if formated_account_id is not None:
        account = AccountRepository().get_account(formated_account_id)
        formated_account_id = account.id if account else None

    bill_repository = BillRepository()
    bill_repository.insert_bill(
        bar_code=formated_bar_code,
        value=formated_value,
        due_date=formated_vencimento,
        reference=reference,
        suplyer=suplyer,
        bill_type=bill_type,
        pix_key=pix_key or None,
        pix_payload=pix_payload or None,
        pix_image=pix_image or None,
        obs=obs,
        account_id=formated_account_id,
    )

    flash("Conta cadastrada com sucesso!", "success")
    return redirect(url_for("bp_bills.bills"))
