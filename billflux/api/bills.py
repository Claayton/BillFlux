"""Endpoints de contas a pagar da API JSON (lista, cadastro e pagamento)."""

from datetime import date, datetime, timedelta
from decimal import Decimal, InvalidOperation

from flask import request

from billflux.api import (
    bp,
    api_error,
    api_login_required,
    api_response,
    br_to_decimal,
)
from billflux.config import settings
from billflux.controlers.bills import _account_context, _build_stats
from billflux.infra.repository.account_repository import AccountRepository
from billflux.infra.repository.bill_repository import BillRepository
from billflux.services.barcode import to_barcode


def _as_date(value):
    """Normaliza datetime/date para date."""
    return value.date() if isinstance(value, datetime) else value


def _serialize_account(account):
    return {
        "id": account.id,
        "name": account.name,
        "type": account.type,
        "color": account.color,
    }


def _bill_status(bill, today):
    tomorrow = today + timedelta(days=1)
    due = _as_date(bill.due_date) if bill.due_date else None
    if bill.status:
        return "paga"
    if not due:
        return "semvenc"
    if due < today:
        return "vencida"
    if due == today:
        return "hoje"
    if due == tomorrow:
        return "amanha"
    return "pendente"


def _serialize_bill(bill, account_names, today):
    due = _as_date(bill.due_date) if bill.due_date else None
    return {
        "id": bill.id,
        "status": _bill_status(bill, today),
        "reference": bill.reference,
        "suplyer": bill.suplyer,
        "bill_type": bill.bill_type,
        "category": account_names.get(bill.account_id) if bill.account_id else None,
        "account_id": bill.account_id,
        "due_date": due.isoformat() if due else None,
        "payday": bill.payday.isoformat() if bill.payday else None,
        "value": float(bill.value or 0),
        "value_from_payment": float(bill.value_from_payment or 0),
        "bar_code": bill.bar_code,
        "pix_key": bill.pix_key,
        "pix_payload": bill.pix_payload,
        "pix_image": bill.pix_image,
        "obs": bill.obs,
        "date_from_add": bill.date_from_add.isoformat(),
        "overdue_days": (due - today).days if due and due < today else None,
    }


def _bills_payload():
    repository = BillRepository()
    repository.cleanup_pix_data(settings.pix.retention_days)
    list_bills = repository.get_bills()
    today = date.today()
    stats = _build_stats(list_bills, today)
    account_names, account_groups = _account_context()

    return {
        "today": today.isoformat(),
        "stats": {
            "open": float(stats["open"]),
            "overdue": float(stats["overdue"]),
            "paid_month": float(stats["paid_month"]),
            "total": stats["total"],
        },
        "account_groups": [
            {
                "label": group["label"],
                "accounts": [_serialize_account(a) for a in group["accounts"]],
            }
            for group in account_groups
        ],
        "bills": [_serialize_bill(b, account_names, today) for b in list_bills],
    }


def _parse_bill_fields(data):
    """Extrai e valida os campos comuns a criar/editar conta."""
    value = br_to_decimal(data.get("value"))
    vencimento = data.get("due_date") or data.get("vencimento")
    if value is None or value <= 0 or not vencimento:
        return None, "Valor e vencimento são obrigatórios."

    try:
        formated_value = value
        formated_vencimento = datetime.strptime(vencimento, "%Y-%m-%d")
    except (InvalidOperation, ValueError, TypeError):
        return None, "Valor ou vencimento inválidos."

    bar_code = (data.get("bar_code") or "").strip() or None
    try:
        formated_bar_code = to_barcode(bar_code) or bar_code if bar_code else None
    except (InvalidOperation, ValueError):
        return None, "Código de barras inválido."

    account_id = data.get("account_id")
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
        "reference": (data.get("reference") or "").strip() or None,
        "suplyer": (data.get("suplyer") or "").strip() or None,
        "bill_type": (data.get("bill_type") or "").strip() or None,
        "account_id": formated_account_id,
        "pix_key": (data.get("pix_key") or "").strip() or None,
        "obs": (data.get("obs") or "").strip() or None,
        "bar_code": formated_bar_code,
    }

    # Marcar/desmarcar como paga a partir do formulário.
    if "status" in data:
        fields["status"] = bool(data.get("status"))
        if fields["status"]:
            fields["payday"] = datetime.now()
            fields["value_from_payment"] = formated_value
        else:
            fields["payday"] = None
            fields["value_from_payment"] = None

    return fields, None


@bp.route("/bills")
@api_login_required
def bills():
    """Lista as contas com resumo financeiro e categorias."""
    return api_response(_bills_payload())


@bp.route("/bills", methods=["POST"])
@api_login_required
def bills_create():
    """Cadastra uma nova conta a pagar."""
    fields, error = _parse_bill_fields(request.get_json(silent=True) or {})
    if error:
        return api_error(error, 400)
    BillRepository().insert_bill(**fields)
    return api_response(_bills_payload(), status=201)


@bp.route("/bills/<int:bill_id>", methods=["PUT"])
@api_login_required
def bills_edit(bill_id):
    """Atualiza uma conta existente."""
    repository = BillRepository()
    if not repository.get_bill(bill_id):
        return api_error("Conta não encontrada.", 404)

    fields, error = _parse_bill_fields(request.get_json(silent=True) or {})
    if error:
        return api_error(error, 400)
    repository.update_bill(bill_id, **fields)
    return api_response(_bills_payload())


@bp.route("/bills/<int:bill_id>/pay", methods=["POST"])
@api_login_required
def bills_pay(bill_id):
    """Marca uma conta como paga."""
    repository = BillRepository()
    if not repository.pay_bill(bill_id):
        return api_error("Conta não encontrada.", 404)
    return api_response(_bills_payload())


@bp.route("/bills/<int:bill_id>", methods=["DELETE"])
@api_login_required
def bills_delete(bill_id):
    """Exclui uma conta."""
    repository = BillRepository()
    if not repository.delete_bill(bill_id):
        return api_error("Conta não encontrada.", 404)
    return api_response(_bills_payload())
