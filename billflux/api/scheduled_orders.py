"""Endpoints de encargos/agenda de pedidos a clientes (API JSON)."""

import json
from datetime import date, datetime
from decimal import Decimal

from flask import request

from billflux.api import bp, api_error, api_login_required, api_response, br_to_decimal
from billflux.infra.repository.customer_repository import CustomerRepository
from billflux.infra.repository.scheduled_order_repository import (
    ORDER_STATUSES,
    ScheduledOrderRepository,
)


def _serialize(order):
    items_raw = json.loads(order.items) if order.items else []
    return {
        "id": order.id,
        "customer_id": order.customer_id,
        "customer_name": order.customer_name or "",
        "order_date": order.order_date.isoformat() if order.order_date else None,
        "order_time": order.order_time or "",
        "status": order.status,
        "obs": order.obs or "",
        "total": str(order.total or Decimal("0")),
        "items": items_raw,
        "created_at": order.created_at.isoformat() if order.created_at else None,
    }


def _parse_order_payload(data):
    """Valida y normaliza el payload de alta/edición de un encargo."""
    customer_id = data.get("customer_id")
    customer_name = (data.get("customer_name") or "").strip()
    if customer_id:
        customer = CustomerRepository().get_customer(int(customer_id))
        if not customer:
            return None, "Cliente no encontrado."
        customer_name = customer.name
    elif not customer_name:
        return None, "Indique el cliente (o seleccione uno del catálogo)."

    order_date = None
    if data.get("order_date"):
        try:
            order_date = date.fromisoformat(data["order_date"])
        except (TypeError, ValueError):
            return None, "Fecha inválida."

    order_time = (data.get("order_time") or "").strip() or None
    status = (data.get("status") or "pendente").strip().lower()
    if status not in ORDER_STATUSES:
        return None, "Estado inválido."
    obs = (data.get("obs") or "").strip() or None

    items = []
    for raw in data.get("items") or []:
        qty = int(raw.get("quantity") or 0)
        unit_price = br_to_decimal(raw.get("unit_price")) or Decimal("0")
        if qty <= 0:
            continue
        items.append(
            {
                "product_id": raw.get("product_id"),
                "name": (raw.get("name") or "").strip(),
                "quantity": qty,
                "unit_price": str(unit_price),
                "total": str(Decimal(str(qty)) * unit_price),
            }
        )
    total = sum(Decimal(str(i["total"])) for i in items)

    payload = {
        "customer_id": int(customer_id) if customer_id else None,
        "customer_name": customer_name,
        "order_date": order_date,
        "order_time": order_time,
        "status": status,
        "obs": obs,
        "items": items,
        "total": total,
    }
    return payload, None


@bp.route("/scheduled-orders")
@api_login_required
def scheduled_orders_list():
    data = ScheduledOrderRepository().list_orders(
        order_date=(
            request.args.get("date", type=date.fromisoformat)
            if request.args.get("date")
            else None
        ),
        status=(request.args.get("status") or "").strip() or None,
        search=(request.args.get("q") or "").strip() or None,
    )
    return api_response({"orders": [_serialize(o) for o in data]})


@bp.route("/scheduled-orders", methods=["POST"])
@api_login_required
def scheduled_orders_create():
    data = request.get_json(silent=True) or {}
    payload, error = _parse_order_payload(data)
    if error:
        return api_error(error, 400)
    order = ScheduledOrderRepository().create_order(**payload)
    return api_response({"order": _serialize(order)}, status=201)


@bp.route("/scheduled-orders/<int:order_id>")
@api_login_required
def scheduled_orders_detail(order_id):
    order = ScheduledOrderRepository().get_order(order_id)
    if not order:
        return api_error("Pedido no encontrado.", 404)
    return api_response({"order": _serialize(order)})


@bp.route("/scheduled-orders/<int:order_id>", methods=["PUT"])
@api_login_required
def scheduled_orders_update(order_id):
    repository = ScheduledOrderRepository()
    if not repository.get_order(order_id):
        return api_error("Pedido no encontrado.", 404)
    data = request.get_json(silent=True) or {}
    payload, error = _parse_order_payload(data)
    if error:
        return api_error(error, 400)
    items = payload.pop("items")
    order = repository.update_order(order_id, payload, items=items)
    return api_response({"order": _serialize(order)})


@bp.route("/scheduled-orders/<int:order_id>/status", methods=["POST"])
@api_login_required
def scheduled_orders_status(order_id):
    data = request.get_json(silent=True) or {}
    status = (data.get("status") or "").strip().lower()
    if status not in ORDER_STATUSES:
        return api_error("Estado inválido.", 400)
    order = ScheduledOrderRepository().set_status(order_id, status)
    if not order:
        return api_error("Pedido no encontrado.", 404)
    return api_response({"order": _serialize(order)})


@bp.route("/scheduled-orders/<int:order_id>", methods=["DELETE"])
@api_login_required
def scheduled_orders_delete(order_id):
    if not ScheduledOrderRepository().delete_order(order_id):
        return api_error("Pedido no encontrado.", 404)
    return api_response({"ok": True})
