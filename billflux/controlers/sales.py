"""File to instantiate the blueprint for the daily sales page"""

from datetime import date, datetime
from decimal import Decimal, InvalidOperation

from flask import flash, redirect, request, url_for
from flask.blueprints import Blueprint
from flask.templating import render_template

from billflux.controlers.auth import login_required
from billflux.infra.repository.sale_repository import SaleRepository

bp = Blueprint("bp_sales", __name__)


def _build_summary(sales, today):
    """Resumo das vendas exibido acima da tabela (apenas exibição)."""
    today_total = Decimal("0")
    month_total = Decimal("0")
    days_with_sale = 0

    for sale in sales:
        total = sale.total or Decimal("0")
        if sale.date == today:
            today_total += total
        if sale.date.year == today.year and sale.date.month == today.month:
            month_total += total
            days_with_sale += 1

    avg = month_total / days_with_sale if days_with_sale else Decimal("0")

    return {
        "today": today_total,
        "month": month_total,
        "days": days_with_sale,
        "avg": avg,
    }


@bp.route("/sales/", methods=["GET", "POST"])
@bp.route("/sales", methods=["GET", "POST"])
@login_required
def sales():
    """Lists daily sales and handles the daily launch form."""

    repository = SaleRepository()
    if request.method == "POST":
        return _save_sale(repository)

    list_sales = repository.get_sales()
    today = date.today()
    summary = _build_summary(list_sales, today)
    return render_template(
        "sales.html",
        sales_list=list_sales,
        summary=summary,
        active="sales",
        today=today,
    )


def _save_sale(repository):
    """Cria ou atualiza (upsert pela data) o lançamento do dia."""

    sale_date = request.form.get("date")
    total = request.form.get("total")
    obs = (request.form.get("obs") or "").strip() or None

    if not sale_date or not total:
        flash("Data e total são obrigatórios.", "error")
        return redirect(url_for("bp_sales.sales"))

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
        return redirect(url_for("bp_sales.sales"))

    if formated_total <= 0:
        flash("O total deve ser maior que zero.", "error")
        return redirect(url_for("bp_sales.sales"))

    existing = repository.get_sale_by_date(formated_date)
    if existing:
        repository.insert_sale(formated_date, formated_total, obs)
        flash(f"Venda de {formated_date:%d/%m/%Y} atualizada!", "success")
    else:
        repository.insert_sale(formated_date, formated_total, obs)
        flash(f"Venda de {formated_date:%d/%m/%Y} lançada!", "success")
    return redirect(url_for("bp_sales.sales"))


@bp.route("/sales/delete/<int:sale_id>", methods=["POST"])
@login_required
def delete_sale(sale_id):
    """Deletes a daily sale."""

    repository = SaleRepository()
    if repository.delete_sale(sale_id):
        flash("Venda excluída.", "success")
    else:
        flash("Venda não encontrada.", "error")
    return redirect(url_for("bp_sales.sales"))
