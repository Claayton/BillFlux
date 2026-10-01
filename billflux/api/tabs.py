"""Endpoints de comandas (tabs) da API JSON.

Reutiliza o mesmo parse de pagamento, o mesmo gerador de recibo e as mesmas
regras de fiado do PDV (importados de `billflux.api.pdv` / `services.credit`)
para o fechamento da comanda ser idêntico ao de uma venda normal.
"""

from decimal import Decimal

from flask import request, session

from billflux.api import bp, api_error, api_login_required, api_response, br_to_decimal
from billflux.api.pdv import _build_receipt, _parse_payments_payload
from billflux.domain.models.tab import Tab
from billflux.infra.repository.tab_repository import TabRepository, tab_label
from billflux.services.audit import audit
from billflux.services.credit import ensure_fiado_customer, register_order_credit


def _serialize_item(item):
    return {
        "id": item.id,
        "product_id": item.product_id,
        "unit_id": item.unit_id,
        "name": item.name,
        "quantity": item.quantity,
        "unit_price": float(item.unit_price),
        "total": float(item.total),
        "factor": item.factor or 1,
    }


def _serialize(tab: Tab, items=None, counts=None):
    item_count, units_count = counts if counts else (None, None)
    if items is not None:
        item_count = len(items)
        units_count = sum(i.quantity for i in items)
    data = {
        "id": tab.id,
        "number": tab.number,
        "label": tab_label(tab.number),
        "identification": tab.identification,
        "status": tab.status,
        "subtotal": float(tab.subtotal or 0),
        "discount": float(tab.discount or 0),
        "total": float(tab.total or 0),
        "order_id": tab.order_id,
        "print_count": tab.print_count or 0,
        "opened_at": tab.opened_at.isoformat() if tab.opened_at else None,
        "closed_at": tab.closed_at.isoformat() if tab.closed_at else None,
        "canceled_at": tab.canceled_at.isoformat() if tab.canceled_at else None,
        "opened_by": tab.opened_by or "",
        "closed_by": tab.closed_by or "",
        "canceled_by": tab.canceled_by or "",
        "item_count": item_count,
        "units_count": units_count,
    }
    if items is not None:
        data["items"] = [_serialize_item(item) for item in items]
    return data


@bp.route("/tabs", methods=["POST"])
@api_login_required
def create_tab():
    """Abre uma comanda com os itens do carrinho e baixa o estoque."""
    data = request.get_json(silent=True) or {}
    identification = (data.get("identification") or "").strip()
    items = data.get("items")
    if not isinstance(items, list):
        items = []
    if not identification:
        return api_error("Informe a identificação da comanda.", 400)
    if not items:
        return api_error("Adicione ao menos um item à comanda.", 400)

    repository = TabRepository()
    try:
        tab = repository.create_tab(
            identification=identification,
            items=items,
            opened_by=session.get("user"),
        )
    except ValueError as error:
        return api_error(str(error), 400)

    audit(
        "tab.open",
        entity="tab",
        entity_id=tab.id,
        details={
            "number": tab.number,
            "identification": tab.identification,
            "total": float(tab.total),
        },
    )
    detail = repository.get_tab_items(tab.id)
    return api_response({"tab": _serialize(tab, items=detail)}, status=201)


@bp.route("/tabs")
@api_login_required
def list_tabs():
    """Lista comandas (padrão: abertas), com busca por número/identificação."""
    status = (request.args.get("status") or "open").strip().lower()
    if status not in ("open", "closed", "canceled", "all"):
        return api_error("Status inválido.", 400)
    search = request.args.get("q", "").strip() or None

    repository = TabRepository()
    tabs = repository.list_tabs(
        status=None if status == "all" else status, search=search
    )
    counts = repository.items_counts([t.id for t in tabs])
    return api_response(
        {"tabs": [_serialize(t, counts=counts.get(t.id)) for t in tabs]}
    )


@bp.route("/tabs/<int:tab_id>")
@api_login_required
def get_tab(tab_id):
    """Detalhe da comanda com itens (para retomar o atendimento no PDV)."""
    repository = TabRepository()
    tab = repository.get_tab(tab_id)
    if not tab:
        return api_error("Comanda não encontrada.", 404)
    return api_response(
        {"tab": _serialize(tab, items=repository.get_tab_items(tab_id))}
    )


@bp.route("/tabs/<int:tab_id>/items", methods=["PUT"])
@api_login_required
def set_tab_items(tab_id):
    """Substitui os itens da comanda aplicando os deltas de estoque."""
    data = request.get_json(silent=True) or {}
    items = data.get("items")
    if not isinstance(items, list):
        return api_error("Itens da comanda inválidos.", 400)

    repository = TabRepository()
    try:
        tab = repository.set_tab_items(tab_id, items)
    except ValueError as error:
        return api_error(str(error), 400)
    if not tab:
        return api_error("Comanda não encontrada.", 404)

    audit(
        "tab.update",
        entity="tab",
        entity_id=tab.id,
        details={"number": tab.number, "total": float(tab.total)},
    )
    detail = repository.get_tab_items(tab.id)
    return api_response({"tab": _serialize(tab, items=detail)})


@bp.route("/tabs/<int:tab_id>/close", methods=["POST"])
@api_login_required
def close_tab(tab_id):
    """Fecha a comanda: gera a venda definitiva (sem baixa dupla de estoque),
    registra pagamento, débito fiado (se houver) e devolve o recibo."""
    from billflux.infra.repository.cash_register_repository import (
        CashRegisterRepository,
    )

    if not CashRegisterRepository().get_open():
        return api_error(
            "Nenhum caixa aberto. Abra o caixa antes de registrar vendas.", 400
        )

    data = request.get_json(silent=True) or {}
    payments, method_id, payments_error = _parse_payments_payload(data)
    if payments_error:
        return api_error(payments_error, 400)

    discount = br_to_decimal(data.get("discount"))
    if discount is None:
        discount = Decimal("0")
    if discount < 0:
        return api_error("Desconto inválido.", 400)

    obs = (data.get("obs") or "").strip() or None
    customer_id = None
    raw_customer = data.get("customer_id")
    if raw_customer:
        try:
            customer_id = int(raw_customer)
        except (TypeError, ValueError):
            customer_id = None

    selected_method_ids = (
        [mid for mid, _ in payments] if payments is not None else [method_id]
    )
    try:
        ensure_fiado_customer(selected_method_ids, customer_id)
    except ValueError as error:
        return api_error(str(error), 400)

    repository = TabRepository()
    try:
        result = repository.close_tab(
            tab_id,
            payment_method_id=method_id,
            payments=payments,
            discount=discount,
            obs=obs,
            customer_id=customer_id,
            closed_by=session.get("user"),
        )
    except ValueError as error:
        return api_error(str(error), 400)
    if not result:
        return api_error("Comanda não encontrada.", 404)

    tab, order = result
    register_order_credit(order.id, customer_id)
    audit(
        "tab.close",
        entity="tab",
        entity_id=tab.id,
        details={
            "number": tab.number,
            "order_id": order.id,
            "total": float(order.total),
        },
    )
    return api_response(
        {"order": _build_receipt(order.id), "tab": _serialize(tab)}, status=201
    )


@bp.route("/tabs/<int:tab_id>/cancel", methods=["POST"])
@api_login_required
def cancel_tab(tab_id):
    """Cancela a comanda aberta devolvendo os itens ao estoque (histórico
    do cancelamento é preservado; nada é apagado)."""
    repository = TabRepository()
    try:
        tab = repository.cancel_tab(tab_id, canceled_by=session.get("user"))
    except ValueError as error:
        return api_error(str(error), 400)
    if not tab:
        return api_error("Comanda não encontrada.", 404)

    audit(
        "tab.cancel",
        entity="tab",
        entity_id=tab.id,
        details={"number": tab.number, "identification": tab.identification},
    )
    return api_response({"tab": _serialize(tab)})


@bp.route("/tabs/<int:tab_id>/print", methods=["POST"])
@api_login_required
def print_tab(tab_id):
    """Registra impressão/reimpressão da comanda (contador de histórico)."""
    repository = TabRepository()
    tab = repository.register_print(tab_id)
    if not tab:
        return api_error("Comanda não encontrada.", 404)
    return api_response(
        {"tab": _serialize(tab, items=repository.get_tab_items(tab_id))}
    )
