"""Endpoints de vendas da API JSON (lista, lançamento avulso e exclusão)."""

from datetime import date, datetime
from decimal import Decimal, InvalidOperation

from flask import request

from billflux.api import bp, api_error, api_login_required, api_response
from billflux.controlers.sales import _build_periods, _combine_sales
from billflux.infra.repository.order_repository import OrderRepository
from billflux.infra.repository.payment_method_repository import (
    PaymentMethodRepository,
)
from billflux.infra.repository.sale_repository import SaleRepository


def _sales_payload():
    """Dados completos da página de vendas (períodos + lista combinada)."""
    list_sales = SaleRepository().get_sales()
    orders = OrderRepository().get_orders()
    today = date.today()
    periods = _build_periods(list_sales, orders, today)

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
                "total": str(item["total"]),
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
