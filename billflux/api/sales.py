"""Endpoints de vendas da API JSON (lista, lançamento avulso e exclusão)."""

from datetime import date, datetime, timedelta
from decimal import Decimal, InvalidOperation

from flask import request

from billflux.api import bp, api_error, api_login_required, api_response
from billflux.infra.repository.order_repository import OrderRepository
from billflux.infra.repository.payment_method_repository import (
    PaymentMethodRepository,
)
from billflux.infra.repository.product_repository import ProductRepository
from billflux.infra.repository.receivable_repository import ReceivableRepository
from billflux.infra.repository.sale_repository import SaleRepository
from billflux.infra.repository.customer_repository import CustomerRepository
from billflux.infra.repository.cash_register_repository import CashRegisterRepository
from billflux.services.audit import audit
from billflux.services.credit import fiado_amount_for_order, get_fiado_method_ids


def _build_range_summary(sales, orders, start, end):
    """Resumo das vendas (total, nº de vendas, dias e média) num período.

    Considera lançamentos manuais (sales) e pedidos fechados no PDV (orders),
    ignorando os cancelados."""
    total = Decimal("0")
    count = 0
    days = set()

    for sale in sales:
        if sale.cancelled:
            continue
        if start <= sale.date <= end:
            total += sale.total
            count += 1
            days.add(sale.date)

    for order in orders:
        if order.cancelled:
            continue
        order_date = order.created_at.date()
        if start <= order_date <= end:
            total += order.total
            count += 1
            days.add(order_date)

    avg = total / len(days) if days else Decimal("0")

    return {"total": total, "count": count, "days": len(days), "avg": avg}


def _build_periods(sales, orders, today):
    """Resumos por período."""
    month_start = today.replace(day=1)
    prev_month_end = month_start - timedelta(days=1)
    prev_month_start = prev_month_end.replace(day=1)

    raw = {
        "hoje": _build_range_summary(sales, orders, today, today),
        "7d": _build_range_summary(sales, orders, today - timedelta(days=6), today),
        "mes": _build_range_summary(sales, orders, month_start, today),
        "mes_anterior": _build_range_summary(
            sales, orders, prev_month_start, prev_month_end
        ),
    }

    return {
        key: {
            "total": str(value["total"]),
            "count": value["count"],
            "days": value["days"],
            "avg": str(value["avg"]),
        }
        for key, value in raw.items()
    }


def _order_detail(order):
    """Dados extras de um pedido PDV: hora e itens (nome + quantidade)."""
    repository = OrderRepository()
    items_detail = repository.get_order_items(order.id)
    products = {}
    for item in items_detail:
        product = ProductRepository().get_product(item.product_id)
        products[item.product_id] = product.name if product else "Item"
    return {
        "time": order.created_at.strftime("%H:%M") if order.created_at else None,
        "items": [
            {"name": products[item.product_id], "quantity": item.quantity}
            for item in items_detail
        ],
    }


def _parse_register_dt(value):
    """Converte 'YYYY-MM-DD HH:MM:SS' (ou datetime) em datetime."""
    if not value:
        return None
    if isinstance(value, datetime):
        return value
    try:
        return datetime.strptime(value, "%Y-%m-%d %H:%M:%S")
    except (TypeError, ValueError):
        return None


def _caixa_sessions():
    """Sessões de caixa mais recentes (inclusive a aberta), ordenadas."""
    registers = CashRegisterRepository().get_history(limit=60)
    sessions = [
        {
            "id": cr.id,
            "opened_at": cr.opened_at,
            "closed_at": cr.closed_at,
            "status": cr.status,
        }
        for cr in registers
    ]
    sessions.sort(key=lambda s: s["opened_at"] or "")
    return sessions


def _caixa_id_for_datetime(when, sessions):
    """Sessão de caixa que contém o instante informado (ou None)."""
    for session in sessions:
        opened = _parse_register_dt(session["opened_at"])
        closed = _parse_register_dt(session["closed_at"])
        if opened and opened <= when and (closed is None or when <= closed):
            return session["id"]
    return None


def _caixa_id_for_day(day, sessions):
    """Sessão de caixa que cobre o dia (vendas avulsas não têm hora)."""
    found = None
    for session in sessions:
        opened = _parse_register_dt(session["opened_at"])
        closed = _parse_register_dt(session["closed_at"])
        if not opened:
            continue
        if opened.date() <= day and (closed is None or closed.date() >= day):
            if found is None or opened > _parse_register_dt(found["opened_at"]):
                found = session
    return found["id"] if found else None


def _combine_sales(sales, orders, payment_names, caixa_opened_at=None, sessions=None):
    """Junta vendas avulsas (manuais) e pedidos do PDV numa única lista.

    `caixa_opened_at` (datetime ou None) marca o início do caixa aberto e
    permite sinalizar quais vendas pertencem ao caixa atual (`in_caixa`).
    `sessions` associa cada venda à sessão de caixa (`caixa_id`), pra separar
    onde um caixa foi fechado e outro aberto."""

    sessions = sessions or []
    combined = []
    for sale in sales:
        combined.append(
            {
                "kind": "manual",
                "id": sale.id,
                "date": sale.date,
                "total": sale.total,
                "obs": sale.obs,
                "time": None,
                "items": [],
                "payment": None,
                "cancelled": sale.cancelled,
                "caixa_id": _caixa_id_for_day(sale.date, sessions),
                "in_caixa": (
                    caixa_opened_at is not None and sale.date >= caixa_opened_at.date()
                ),
            }
        )
    for order in orders:
        detail = _order_detail(order)
        combined.append(
            {
                "kind": "pdv",
                "id": order.id,
                "date": order.created_at.date(),
                "total": order.total,
                "obs": order.obs,
                "time": detail["time"],
                "items": detail["items"],
                "payment": payment_names.get(order.payment_method_id, "—"),
                "cancelled": order.cancelled,
                "caixa_id": _caixa_id_for_datetime(order.created_at, sessions),
                "in_caixa": (
                    caixa_opened_at is not None and order.created_at >= caixa_opened_at
                ),
            }
        )
    return sorted(combined, key=lambda item: item["date"], reverse=True)


def _sales_payload():
    """Dados completos da página de vendas (períodos + lista combinada)."""
    list_sales = SaleRepository().get_sales()
    orders = OrderRepository().get_orders()
    open_register = CashRegisterRepository().get_open()
    caixa_opened_at = None
    if open_register:
        try:
            caixa_opened_at = datetime.strptime(
                open_register.opened_at, "%Y-%m-%d %H:%M:%S"
            )
        except (TypeError, ValueError):
            caixa_opened_at = None

    today = date.today()
    periods = {
        key: {**p, "total": float(p["total"]), "avg": float(p["avg"])}
        for key, p in _build_periods(list_sales, orders, today).items()
    }

    payment_names = {
        method.id: method.name for method in PaymentMethodRepository().get_methods()
    }
    sessions = _caixa_sessions()
    combined = _combine_sales(
        list_sales, orders, payment_names, caixa_opened_at, sessions
    )

    return {
        "today": today.isoformat(),
        "caixa": {
            "open": open_register is not None,
            "opened_at": open_register.opened_at if open_register else None,
        },
        "caixa_sessions": sessions,
        "periods": periods,
        "sales": [
            {
                "kind": item["kind"],
                "id": item["id"],
                "date": item["date"].isoformat(),
                "total": float(item["total"]),
                "obs": item["obs"],
                "time": item["time"],
                "items": item["items"],
                "payment": item["payment"],
                "cancelled": item["cancelled"],
                "caixa_id": item["caixa_id"],
                "in_caixa": item["in_caixa"],
            }
            for item in combined
        ],
    }


def _normalize_total(raw):
    """Aceita '150,50', '150.50' ou '150' e devolve Decimal."""
    text = raw.strip()
    if "," in text:
        text = text.replace(".", "").replace(",", ".")
    return Decimal(text)


@bp.route("/sales")
@api_login_required
def sales_list():
    """Lista vendas avulsas + pedidos do PDV, com resumos por período."""
    return api_response(_sales_payload())


@bp.route("/sales", methods=["POST"])
@api_login_required
def sales_create():
    """Cria ou atualiza (upsert pela data) o lançamento avulso do dia."""
    formated_date, formated_total, obs, error = _parse_sale_data(
        request.get_json(silent=True) or {}
    )
    if error:
        return api_error(error, 400)

    SaleRepository().insert_sale(formated_date, formated_total, obs)
    return api_response(_sales_payload(), status=201)


@bp.route("/sales/<int:sale_id>", methods=["DELETE"])
@api_login_required
def sales_delete(sale_id):
    """Exclui definitivamente um lançamento avulso de venda."""
    if SaleRepository().delete_sale(sale_id):
        return api_response(_sales_payload())
    return api_error("Venda não encontrada.", 404)


@bp.route("/sales/<int:sale_id>/cancel", methods=["POST"])
@api_login_required
def sales_cancel(sale_id):
    """Cancela uma venda avulsa mantendo-a na lista (marca como cancelada)."""
    repository = SaleRepository()
    sale = repository.get_sale(sale_id)
    if not sale:
        return api_error("Venda não encontrada.", 404)
    if not repository.cancel_sale(sale_id):
        return api_error("Venda já cancelada.", 400)
    data = request.get_json(silent=True) or {}
    audit(
        "sale.cancel",
        entity="sale",
        entity_id=sale_id,
        details={
            "total": str(sale.total),
            "reason": (data.get("reason") or "").strip() or None,
        },
    )
    return api_response(_sales_payload())


def _parse_sale_data(data):
    """Valida data/total de uma venda avulsa e devolve (date, Decimal, obs)."""
    sale_date = data.get("date")
    total = data.get("total")
    obs = (data.get("obs") or "").strip() or None

    if not sale_date or not total:
        return None, None, None, "Data e total são obrigatórios."

    try:
        formated_date = datetime.strptime(sale_date, "%Y-%m-%d").date()
        formated_total = _normalize_total(total)
    except (InvalidOperation, ValueError):
        return None, None, None, "Data ou valor inválidos."

    if formated_total <= 0:
        return None, None, None, "O total deve ser maior que zero."

    return formated_date, formated_total, obs, None


@bp.route("/sales/<int:sale_id>", methods=["PUT"])
@api_login_required
def sales_edit(sale_id):
    """Edita uma venda avulsa (valor, data e observações)."""
    repository = SaleRepository()
    sale = repository.get_sale(sale_id)
    if not sale:
        return api_error("Venda não encontrada.", 404)
    if sale.cancelled:
        return api_error("Venda cancelada não pode ser editada.", 400)

    formated_date, formated_total, obs, error = _parse_sale_data(
        request.get_json(silent=True) or {}
    )
    if error:
        return api_error(error, 400)

    repository.delete_sale(sale_id)
    repository.insert_sale(formated_date, formated_total, obs)
    return api_response(_sales_payload())


def _parse_order_items(data):
    """Extrai e valida os itens de um pedido PDV."""
    items = data.get("items") or []
    if not isinstance(items, list) or not items:
        return None, "Adicione ao menos um item ao pedido."

    cart = []
    for item in items:
        try:
            product_id = int(item.get("product_id"))
            quantity = int(item.get("quantity"))
        except (TypeError, ValueError):
            continue
        if quantity > 0:
            cart.append((product_id, quantity))

    if not cart:
        return None, "Adicione ao menos um item ao pedido."
    return cart, None


@bp.route("/sales/orders/<int:order_id>", methods=["GET"])
@api_login_required
def order_detail(order_id):
    """Dados de edição de um pedido PDV (itens com ids e forma de pagamento)."""
    repository = OrderRepository()
    order = repository.get_order(order_id)
    if not order:
        return api_error("Pedido não encontrado.", 404)

    items = repository.get_order_items(order_id)
    products = {}
    for item in items:
        product = ProductRepository().get_product(item.product_id)
        products[item.product_id] = product

    return api_response(
        {
            "order": {
                "id": order.id,
                "obs": order.obs,
                "method_id": order.payment_method_id,
                "items": [
                    {
                        "product_id": item.product_id,
                        "name": (
                            products[item.product_id].name
                            if products.get(item.product_id)
                            else "Item"
                        ),
                        "quantity": item.quantity,
                        "unit_price": float(item.unit_price),
                        "factor": item.factor or 1,
                    }
                    for item in items
                ],
            }
        }
    )


@bp.route("/sales/orders/<int:order_id>/cancel", methods=["POST"])
@api_login_required
def order_cancel(order_id):
    """Cancela uma venda do PDV mantendo-a na lista: marca como cancelada,
    restaura o estoque dos itens e cancela o débito fiado (se houver)."""
    if OrderRepository().cancel_order(order_id):
        data = request.get_json(silent=True) or {}
        details = {
            "reason": (data.get("reason") or "").strip() or None,
        }
        receivable = ReceivableRepository().cancel_by_order(order_id)
        if receivable:
            details["credit_cancelled"] = round(float(receivable.amount or 0), 2)
            audit(
                "credit.cancel",
                entity="receivable",
                entity_id=receivable.id,
                details={
                    "order_id": order_id,
                    "reason": "venda cancelada",
                    "paid": round(float(receivable.paid_amount or 0), 2),
                },
            )
        audit("order.cancel", entity="order", entity_id=order_id, details=details)
        return api_response(_sales_payload())
    return api_error("Pedido não encontrado ou já cancelado.", 400)


@bp.route("/sales/orders/<int:order_id>", methods=["PUT"])
@api_login_required
def order_edit(order_id):
    """Edita uma venda do PDV (itens, forma de pagamento e observações)."""
    data = request.get_json(silent=True) or {}

    method_id = data.get("method_id")
    try:
        method_id = int(method_id) if method_id else None
    except (TypeError, ValueError):
        method_id = None
    method = PaymentMethodRepository().get_method(method_id) if method_id else None
    if not method or not method.active:
        return api_error("Selecione a forma de pagamento.", 400)

    is_fiado = method.id in get_fiado_method_ids()
    order_repo = OrderRepository()
    order = order_repo.get_order(order_id)
    if not order:
        return api_error("Pedido não encontrado.", 404)
    if is_fiado:
        if not order.customer_id:
            return api_error(
                "Venda fiada: vincule um cliente à venda antes de usar 'Fiado'.",
                400,
            )
        customer = CustomerRepository().get_customer(order.customer_id)
        if not customer or not customer.active:
            return api_error("Cliente da venda inválido para fiado.", 400)

    cart, error = _parse_order_items(data)
    if error:
        return api_error(error, 400)

    obs = (data.get("obs") or "").strip() or None

    try:
        order_repo.update_order(order_id, cart, method.id, obs=obs)
    except ValueError as error_message:
        return api_error(str(error_message), 400)

    # Reconcilia o débito fiado após a edição (forma pode ter mudado)
    receivable_repo = ReceivableRepository()
    cancelled_receivable = receivable_repo.cancel_by_order(
        order_id, reason="venda editada"
    )
    if cancelled_receivable:
        audit(
            "credit.cancel",
            entity="receivable",
            entity_id=cancelled_receivable.id,
            details={
                "order_id": order_id,
                "reason": "venda editada",
                "paid": round(float(cancelled_receivable.paid_amount or 0), 2),
            },
        )
    if is_fiado:
        fiado_total = float(fiado_amount_for_order(order_id))
        if fiado_total > 0:
            receivable_repo.create(
                order_id=order_id,
                customer_id=order.customer_id,
                amount=fiado_total,
                obs=f"Venda #{order_id} (editada)",
            )
            audit(
                "credit.sale",
                entity="order",
                entity_id=order_id,
                details={
                    "customer_id": order.customer_id,
                    "amount": round(fiado_total, 2),
                    "source": "edit",
                },
            )
    return api_response(_sales_payload())


@bp.route("/sales/recibo/<int:sale_id>", methods=["GET"])
@api_login_required
def manual_receipt(sale_id):
    """Recibo de uma venda avulsa, no mesmo formato do recibo do PDV."""
    sale = SaleRepository().get_sale(sale_id)
    if not sale:
        return api_error("Venda não encontrada.", 404)

    receipt = {
        "order_id": sale.id,
        "date": datetime.combine(sale.date, datetime.min.time()).isoformat(),
        "total": float(sale.total),
        "discount": 0.0,
        "obs": sale.obs,
        "payment_method": None,
        "items": [
            {
                "name": "Venda avulsa",
                "quantity": 1,
                "unit_price": float(sale.total),
                "subtotal": float(sale.total),
            }
        ],
    }
    return api_response({"order": receipt})
