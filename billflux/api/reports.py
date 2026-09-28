"""Endpoints de relatórios de estoque da API JSON."""

from datetime import datetime

from flask import request

from billflux.api import bp, api_error, api_login_required, api_response
from billflux.infra.repository.report_repository import ReportRepository

MOVEMENT_TYPES = ("entrada", "saida", "ajuste")


def _serialize_movement(movement):
    return {
        "id": movement.id,
        "product_id": movement.product_id,
        "product_name": movement.product_name,
        "movement_type": movement.movement_type,
        "quantity": movement.quantity,
        "obs": movement.obs or "",
        "created_at": movement.created_at.isoformat(),
    }


def _serialize_product(product):
    deficit = max(int(product.min_stock or 0) - int(product.stock_quantity), 0)
    return {
        "id": product.id,
        "name": product.name,
        "stock_quantity": product.stock_quantity,
        "min_stock": product.min_stock,
        "ideal_stock": product.ideal_stock,
        "category_name": product.category_name or "",
        "deficit": deficit,
        "out_of_stock": product.stock_quantity == 0,
    }


def _parse_date(raw, field):
    """Converte 'YYYY-MM-DD' em datetime; devolve (valor, erro)."""
    if not raw:
        return None, None
    try:
        return datetime.strptime(raw.strip(), "%Y-%m-%d"), None
    except (TypeError, ValueError):
        return None, f"Data '{field}' inválida (use AAAA-MM-DD)."


@bp.route("/reports/movements")
@api_login_required
def reports_movements():
    """Relatório de movimentações de estoque com filtros."""
    args = request.args

    raw_type = (args.get("type") or "").strip().lower()
    if raw_type and raw_type not in MOVEMENT_TYPES:
        return api_error("Tipo de movimentação inválido.", 400)

    product_id = None
    raw_product = args.get("product_id")
    if raw_product:
        try:
            product_id = int(raw_product)
        except (TypeError, ValueError):
            return api_error("Produto inválido.", 400)

    date_from, error = _parse_date(args.get("date_from"), "date_from")
    if error:
        return api_error(error, 400)
    date_to, error = _parse_date(args.get("date_to"), "date_to")
    if error:
        return api_error(error, 400)
    if date_from and date_to and date_from > date_to:
        return api_error("Período inválido: início após fim.", 400)

    try:
        limit = int(args.get("limit", 100))
        offset = int(args.get("offset", 0))
    except (TypeError, ValueError):
        return api_error("Parâmetros de paginação inválidos.", 400)
    limit = max(1, min(limit, 500))
    offset = max(0, offset)

    items, total = ReportRepository().list_movements(
        product_id=product_id,
        movement_type=raw_type or None,
        date_from=date_from,
        date_to=date_to,
        limit=limit,
        offset=offset,
    )
    return api_response(
        {
            "movements": [_serialize_movement(m) for m in items],
            "total": total,
            "limit": limit,
            "offset": offset,
        }
    )


@bp.route("/reports/low-stock")
@api_login_required
def reports_low_stock():
    """Lista de produtos com estoque zerado ou abaixo do mínimo."""
    products = ReportRepository().low_stock_products()
    return api_response(
        {
            "products": [_serialize_product(p) for p in products],
            "count": len(products),
        }
    )
