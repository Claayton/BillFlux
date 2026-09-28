"""Endpoints de inventário (contagem) da API JSON."""

from flask import request

from billflux.api import bp, api_error, api_login_required, api_response
from billflux.infra.repository.product_repository import ProductRepository
from billflux.services.audit import audit


@bp.route("/inventory/count", methods=["POST"])
@api_login_required
def inventory_count():
    """Aplica a contagem do inventário: ajusta o estoque para o valor contado."""
    data = request.get_json(silent=True) or {}
    items = data.get("items")
    if not isinstance(items, list) or not items:
        return api_error("Envie ao menos um produto contado.", 400)

    parsed_by_product = {}
    for entry in items if isinstance(items, list) else []:
        if not isinstance(entry, dict):
            return api_error("Item de contagem inválido.", 400)
        try:
            product_id = int(entry.get("product_id"))
            counted = int(entry.get("counted"))
        except (TypeError, ValueError):
            return api_error("Contagem inválida (produto/quantidade).", 400)
        if counted < 0:
            return api_error("Contagem não pode ser negativa.", 400)
        # produto repetido no payload: a última contagem vence
        parsed_by_product[product_id] = counted
    parsed = list(parsed_by_product.items())

    obs = (data.get("obs") or "").strip() or None
    repository = ProductRepository()
    changes = []
    for product_id, counted in parsed:
        product = repository.get_product(product_id)
        if not product:
            return api_error(f"Produto {product_id} não encontrado.", 404)
        delta = counted - product.stock_quantity
        if delta == 0:
            continue
        updated = repository.adjust_stock(
            product_id=product_id,
            delta=delta,
            obs=obs or f"Inventário: contado {counted}",
            movement_type="ajuste",
        )
        if updated is None:
            return api_error(
                f"Não foi possível ajustar o produto '{product.name}'.", 400
            )
        changes.append(
            {
                "product_id": product.id,
                "name": product.name,
                "before": product.stock_quantity,
                "after": counted,
                "delta": delta,
            }
        )

    audit(
        "inventory.count",
        entity="product",
        details={
            "counted": len(parsed),
            "adjusted": len(changes),
        },
    )
    return api_response(
        {
            "counted": len(parsed),
            "adjusted": len(changes),
            "changes": changes,
        }
    )
