"""File to instantiate the blueprint for the bills page"""

from datetime import date, datetime, timedelta
from decimal import Decimal, InvalidOperation

from flask import flash, redirect, request, url_for
from flask.blueprints import Blueprint
from flask.templating import render_template

from billflux.controlers.auth import login_required
from billflux.config import settings
from billflux.infra.repository.account_repository import AccountRepository
from billflux.infra.repository.bill_repository import BillRepository
from billflux.services.barcode import to_barcode

bp = Blueprint("bp_bills", __name__)


def _account_context():
    """Mapeia id -> nome das categorias e agrupa para os formulários."""
    accounts = AccountRepository().get_accounts()
    names = {account.id: account.name for account in accounts}
    groups = [
        {
            "label": "Receitas",
            "accounts": [a for a in accounts if a.type == "receita"],
        },
        {
            "label": "Despesas",
            "accounts": [a for a in accounts if a.type == "despesa"],
        },
    ]
    return names, groups


@bp.route("/bills/", methods=["GET", "POST"])
@bp.route("/bills", methods=["GET", "POST"])
@login_required
def bills():
    """Mount bills route, and list all bills in the table"""

    bills_repository = BillRepository()
    bills_repository.cleanup_pix_data(settings.pix.retention_days)
    list_bills = bills_repository.get_bills()

    today = date.today()
    stats = _build_stats(list_bills, today)
    account_names, account_groups = _account_context()
    return render_template(
        "bills.html",
        bills_list=list_bills,
        stats=stats,
        account_names=account_names,
        account_groups=account_groups,
        active="bills",
        today=today,
        tomorrow=today + timedelta(days=1),
    )


def _as_date(value):
    """Normaliza datetime/date para date (para comparar com today)."""
    return value.date() if isinstance(value, datetime) else value


def _build_stats(bills, today):
    """Resumo financeiro exibido acima da tabela (apenas exibição)."""
    open_total = Decimal("0")
    overdue_total = Decimal("0")
    paid_month_total = Decimal("0")

    for bill in bills:
        value = bill.value or Decimal("0")
        paid_value = bill.value_from_payment or value
        if not bill.status:
            open_total += value
            if bill.due_date and _as_date(bill.due_date) < today:
                overdue_total += value
        elif bill.payday:
            payday = _as_date(bill.payday)
            if payday.year == today.year and payday.month == today.month:
                paid_month_total += paid_value

    return {
        "open": open_total,
        "overdue": overdue_total,
        "paid_month": paid_month_total,
        "total": len(bills),
    }


@bp.route("/bills/pay/<int:bill_id>", methods=["POST"])
@login_required
def pay_bill(bill_id):
    """Mark a bill as paid"""

    bill_repository = BillRepository()
    if bill_repository.pay_bill(bill_id):
        flash("Conta marcada como paga!", "success")
    else:
        flash("Conta não encontrada.", "error")
    return redirect(url_for("bp_bills.bills"))


@bp.route("/bills/edit", methods=["POST"])
@login_required
def edit_bill():
    """Update an existing bill"""

    bill_id = request.form.get("bill_id")
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

    if not bill_id or not value or not vencimento:
        flash("Valor e vencimento são obrigatórios.", "error")
        return redirect(url_for("bp_bills.bills"))

    try:
        formated_bill_id = int(bill_id)
        formated_value = Decimal(value.replace(",", "."))
        formated_vencimento = datetime.strptime(vencimento, "%Y-%m-%d")
        formated_bar_code = to_barcode(bar_code) or bar_code if bar_code else None
    except (InvalidOperation, ValueError):
        flash("Valor, vencimento ou código de barras inválidos.", "error")
        return redirect(url_for("bp_bills.bills"))

    bill_repository = BillRepository()
    try:
        formated_account_id = int(account_id) if account_id else None
    except (TypeError, ValueError):
        formated_account_id = None
    if formated_account_id is not None:
        account = AccountRepository().get_account(formated_account_id)
        formated_account_id = account.id if account else None
    fields = {
        "value": formated_value,
        "due_date": formated_vencimento,
        "reference": reference,
        "suplyer": suplyer,
        "bill_type": bill_type,
        "account_id": formated_account_id,
        "pix_key": pix_key or None,
        "pix_payload": pix_payload or None,
        "pix_image": pix_image or None,
        "obs": obs,
        "bar_code": formated_bar_code,
    }
    if formated_bill_id and bill_repository.update_bill(formated_bill_id, **fields):
        flash("Conta atualizada com sucesso!", "success")
    else:
        flash("Conta não encontrada.", "error")
    return redirect(url_for("bp_bills.bills"))


@bp.route("/bills/delete/<int:bill_id>", methods=["POST"])
@login_required
def delete_bill(bill_id):
    """Delete a bill"""

    bill_repository = BillRepository()
    if bill_repository.delete_bill(bill_id):
        flash("Conta excluída.", "success")
    else:
        flash("Conta não encontrada.", "error")
    return redirect(url_for("bp_bills.bills"))
