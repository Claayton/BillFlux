"""Endpoints de vendas da API JSON (lista, lançamento avulso e exclusão)."""

from datetime import date, datetime, timedelta
from decimal import Decimal, InvalidOperation

from flask import request

from billflux.api import bp, api_error, api_login_required, api_response
from billflux.infra.repository.order_repository import OrderRepository
from billflux.infra.repository.payment_method_repository import (
    PaymentMethodRepository,
)
from billflux.infra.repository.sale_repository import SaleRepository


def _build_range_summary(sales, orders, start, end):
    """Resumo das vendas (total, nº de vendas, dias e média) num período.

    Considera lançamentos manuais (sales) e pedidos fechados no PDV (orders)."""
    total = Decimal("0")
    count = 0
    days = set()

    for sale in sales:
        if start <= sale.date <= end:
            total += sale.total
            count += 1
            days.add(sale.date)

    for order in orders:
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


def _combine_sales(sales, orders, payment_names):
    """Junta vendas avulsas (manuais) e pedidos do PDV numa única lista."""

    combined = []
    for sale in sales:
        combined.append(
            {
                "kind": "manual",
                "id": sale.id,
                "date": sale.date,
                "total": sale.total,
                "obs": sale.obs,
            }
        )
    for order in orders:
        combined.append(
            {
                "kind": "pdv",
                "id": order.id,
                "date": order.created_at.date(),
                "total": order.total,
                "obs": order.obs,
                "payment": payment_names.get(order.payment_method_id, "—"),
            }
        )
    return sorted(combined, key=lambda item: item["date"], reverse=True)


def _sales_payload():
    """Dados completos da página de vendas (períodos + lista combinada)."""
    list_sales = SaleRepository().get_sales()
    orders = OrderRepository().get_orders()
    today = date.today()
    periods = {
        key: {**p, "total": float(p["total"]), "avg": float(p["avg"])}
        for key, p in _build_periods(list_sales, orders, today).items()
    }

    payment_names = {
        method.id: method.name for method in PaymentMethodRepository().get_methods()
    }
    combined = _combine_sales(list_sales, orders, payment_names)

    return {
        "today": today.isoformat(),
        "periods": periods,
        "sales": [
            {
                "kind": item["kind"],
                "id": item["id"],
                "date": item["date"].isoformat(),
                "total": float(item["total"]),
                "obs": item["obs"],
                "payment": item.get("payment"),
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
    data = request.get_json(silent=True) or {}
    sale_date = data.get("date")
    total = data.get("total")
    obs = (data.get("obs") or "").strip() or None

    if not sale_date or not total:
        return api_error("Data e total são obrigatórios.", 400)

    try:
        formated_date = datetime.strptime(sale_date, "%Y-%m-%d").date()
        formated_total = _normalize_total(total)
    except (InvalidOperation, ValueError):
        return api_error("Data ou valor inválidos.", 400)

    if formated_total <= 0:
        return api_error("O total deve ser maior que zero.", 400)

    SaleRepository().insert_sale(formated_date, formated_total, obs)
    return api_response(_sales_payload(), status=201)


@bp.route("/sales/<int:sale_id>", methods=["DELETE"])
@api_login_required
def sales_delete(sale_id):
    """Exclui um lançamento avulso de venda."""
    if SaleRepository().delete_sale(sale_id):
        return api_response(_sales_payload())
    return api_error("Venda não encontrada.", 404)
