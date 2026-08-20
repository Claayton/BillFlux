"""File to instantiate the blueprint for the daily sales page"""

from datetime import date, datetime, timedelta
from decimal import Decimal, InvalidOperation

from flask import flash, redirect, request, url_for
from flask.blueprints import Blueprint
from flask.templating import render_template

from billflux.controlers.auth import login_required
from billflux.infra.repository.order_repository import OrderRepository
from billflux.infra.repository.payment_method_repository import PaymentMethodRepository
from billflux.infra.repository.sale_repository import SaleRepository

bp = Blueprint("bp_sales", __name__)


def _build_summary(sales, orders, today):
    """Resumo das vendas exibido acima da tabela (apenas exibição).
    Soma o lançamento manual (sales) com os pedidos fechados no PDV (orders)."""
    today_total = Decimal("0")
    month_total = Decimal("0")
    days_with_sale = set()

    for sale in sales:
        total = sale.total or Decimal("0")
        if sale.date == today:
            today_total += total
        if sale.date.year == today.year and sale.date.month == today.month:
            month_total += total
            days_with_sale.add(sale.date)

    for order in orders:
        order_date = order.created_at.date()
        if order_date == today:
            today_total += order.total
        if order_date.year == today.year and order_date.month == today.month:
            month_total += order.total
            days_with_sale.add(order_date)

    days = len(days_with_sale)
    avg = month_total / days if days else Decimal("0")

    return {
        "today": today_total,
        "month": month_total,
        "days": days,
        "avg": avg,
    }


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
    """Resumos por período, com strings JSON-safe para os valores."""
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


def _sales_context():
    """Contexto da página de vendas (métricas por período + lista combinada)."""

    list_sales = SaleRepository().get_sales()
    orders = OrderRepository().get_orders()
    today = date.today()
    periods = _build_periods(list_sales, orders, today)

    payment_names = {
        method.id: method.name for method in PaymentMethodRepository().get_methods()
    }
    combined = _combine_sales(list_sales, orders, payment_names)

    return {
        "sales_list": combined,
        "payment_names": payment_names,
        "periods": periods,
        "active_period": "hoje",
        "active": "sales",
        "today": today,
    }


def _render_sales(context):
    """Renderiza a região dinâmica (HTMX) ou a página completa."""

    if request.headers.get("HX-Request"):
        return render_template("_sales_region.html", **context)
    return render_template("sales.html", **context)


def _after_mutation():
    """Resposta após criar/editar/excluir: fragmento no HTMX, redirect normal."""

    if request.headers.get("HX-Request"):
        return _render_sales(_sales_context())
    return redirect(url_for("bp_sales.sales"))


@bp.route("/sales/", methods=["GET", "POST"])
@bp.route("/sales", methods=["GET", "POST"])
@login_required
def sales():
    """Lists daily sales and handles the daily launch form."""

    if request.method == "POST":
        return _save_sale()
    return _render_sales(_sales_context())


def _save_sale():
    """Cria ou atualiza (upsert pela data) o lançamento do dia."""

    repository = SaleRepository()

    sale_date = request.form.get("date")
    total = request.form.get("total")
    obs = (request.form.get("obs") or "").strip() or None

    if not sale_date or not total:
        flash("Data e total são obrigatórios.", "error")
        return _after_mutation()

    try:
        formated_date = datetime.strptime(sale_date, "%Y-%m-%d").date()
        raw_total = total.strip()
        if "," in raw_total:
            normalized = raw_total.replace(".", "").replace(",", ".")
        else:
            normalized = raw_total
        formated_total = Decimal(normalized)
    except (InvalidOperation, ValueError):
        flash("Data ou valor inválidos.", "error")
        return _after_mutation()

    if formated_total <= 0:
        flash("O total deve ser maior que zero.", "error")
        return _after_mutation()

    existing = repository.get_sale_by_date(formated_date)
    if existing:
        repository.insert_sale(formated_date, formated_total, obs)
        flash(f"Venda de {formated_date:%d/%m/%Y} atualizada!", "success")
    else:
        repository.insert_sale(formated_date, formated_total, obs)
        flash(f"Venda de {formated_date:%d/%m/%Y} lançada!", "success")
    return _after_mutation()


@bp.route("/sales/delete/<int:sale_id>", methods=["POST"])
@login_required
def delete_sale(sale_id):
    """Deletes a daily sale."""

    repository = SaleRepository()
    if repository.delete_sale(sale_id):
        flash("Venda excluída.", "success")
    else:
        flash("Venda não encontrada.", "error")
    return _after_mutation()
