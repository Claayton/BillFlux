"""Endpoints de fiado/crediário (contas a receber) da API JSON."""

from flask import request, session

from billflux.api import bp, api_error, api_login_required, api_response
from billflux.infra.repository.cash_movement_repository import (
    CashMovementRepository,
)
from billflux.infra.repository.cash_register_repository import (
    CashRegisterRepository,
)
from billflux.infra.repository.payment_method_repository import (
    PaymentMethodRepository,
)
from billflux.infra.repository.receivable_repository import ReceivableRepository
from billflux.services.audit import audit


def _balance(receivable):
    if receivable.cancelled:
        return 0.0
    return round(
        max(float(receivable.amount or 0) - float(receivable.paid_amount or 0), 0),
        2,
    )


def _serialize(receivable):
    return {
        "id": receivable.id,
        "order_id": receivable.order_id,
        "customer_id": receivable.customer_id,
        "customer_name": receivable.customer_name,
        "amount": float(receivable.amount),
        "paid": float(receivable.paid_amount),
        "balance": _balance(receivable),
        "cancelled": receivable.cancelled,
        "obs": receivable.obs or "",
        "date": receivable.created_at.isoformat(),
    }


def _list_payload():
    repository = ReceivableRepository()
    status = (request.args.get("status") or "open").strip().lower()
    if status not in ("open", "paid", "all"):
        return None
    search = request.args.get("q", "").strip() or None
    customer_id = None
    raw_customer = request.args.get("customer_id")
    if raw_customer:
        try:
            customer_id = int(raw_customer)
        except (TypeError, ValueError):
            return None
    items = repository.list_receivables(
        status=status, search=search, customer_id=customer_id
    )
    return {
        "items": [_serialize(r) for r in items],
        "totals": repository.totals(),
    }


@bp.route("/receivables")
@api_login_required
def receivables_list():
    """Lista os débitos de clientes (fiado/crediário)."""
    payload = _list_payload()
    if payload is None:
        return api_error("Filtro inválido (status: open, paid ou all).", 400)
    return api_response(payload)


@bp.route("/receivables/<int:receivable_id>/payments", methods=["POST"])
@api_login_required
def receivables_pay(receivable_id):
    """Registra um recebimento sobre um débito (entra no caixa se aberto)."""
    data = request.get_json(silent=True) or {}

    try:
        amount = round(float(data.get("amount")), 2)
    except (TypeError, ValueError):
        return api_error("Informe um valor válido.", 400)
    if amount <= 0:
        return api_error("O valor deve ser maior que zero.", 400)

    method_id = data.get("method_id")
    try:
        method_id = int(method_id) if method_id else None
    except (TypeError, ValueError):
        method_id = None
    method = PaymentMethodRepository().get_method(method_id) if method_id else None
    if not method or not method.active:
        return api_error("Selecione a forma de pagamento.", 400)

    repository = ReceivableRepository()
    receivable = repository.get(receivable_id)
    if not receivable:
        return api_error("Débito não encontrado.", 404)
    if receivable.cancelled:
        return api_error("Débito cancelado.", 400)
    balance = _balance(receivable)
    if balance <= 0:
        return api_error("Débito já quitado.", 400)
    if amount > balance:
        return api_error(f"Valor acima do saldo em aberto (R$ {balance:.2f}).", 400)

    user = session.get("user", "operador")
    try:
        updated = repository.add_payment(
            receivable_id=receivable_id,
            amount=amount,
            method_id=method.id,
            created_by=user,
        )
    except ValueError as error:
        return api_error(str(error), 400)

    in_caixa = False
    open_register = CashRegisterRepository().get_open()
    if open_register:
        movement = CashMovementRepository().create(
            cash_register_id=open_register.id,
            kind="entrada",
            amount=amount,
            created_by=user,
            obs=(
                f"Recebimento fiado: {receivable.customer_name} "
                f"(débito #{receivable.id})"
            ),
        )
        repository.attach_cash_movement(receivable_id, movement.id)
        in_caixa = True

    audit(
        "credit.payment",
        entity="receivable",
        entity_id=receivable_id,
        details={
            "amount": amount,
            "method": method.name,
            "in_caixa": in_caixa,
            "balance_after": _balance(updated),
        },
    )
    return api_response({"receivable": _serialize(updated), "in_caixa": in_caixa})
