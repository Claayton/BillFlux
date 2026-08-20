"""Endpoints de produtos (catálogo e estoque) da API JSON."""

from flask import request

from billflux.api import bp, api_error, api_login_required, api_response, br_to_decimal
from billflux.infra.repository.product_repository import ProductRepository


def _serialize_product(product):
    return {
        "id": product.id,
        "name": product.name,
        "price": float(product.price),
        "cost": float(product.cost),
        "barcode": product.barcode,
        "stock_quantity": product.stock_quantity,
        "min_stock": product.min_stock,
        "obs": product.obs,
        "active": product.active,
    }


def _serialize_movement(movement):
    return {
        "id": movement.id,
        "movement_type": movement.movement_type,
        "quantity": movement.quantity,
        "obs": movement.obs,
        "date": movement.created_at.isoformat(),
    }


def _products_payload():
    repository = ProductRepository()
    return {
        "products": [_serialize_product(p) for p in repository.get_products()],
    }


@bp.route("/products")
@api_login_required
def products_list():
    """Lista o catálogo completo de produtos."""
    return api_response(_products_payload())


@bp.route("/products", methods=["POST"])
@api_login_required
def products_create():
    """Cadastra um novo produto."""
    data = request.get_json(silent=True) or {}
    name = (data.get("name") or "").strip()
    price = br_to_decimal(data.get("price"))
    cost = br_to_decimal(data.get("cost"))
    barcode = (data.get("barcode") or "").strip() or None
    obs = (data.get("obs") or "").strip() or None

    if not name:
        return api_error("Informe o nome do produto.", 400)
    if price is None or price < 0:
        return api_error("Informe um preço válido.", 400)
    if cost is None:
        cost = 0
    elif cost < 0:
        return api_error("Informe um custo válido.", 400)

    try:
        stock = int(data.get("stock_quantity") or 0)
        min_stock = int(data.get("min_stock") or 0)
    except (TypeError, ValueError):
        return api_error("Quantidades inválidas.", 400)
    if stock < 0 or min_stock < 0:
        return api_error("Quantidades inválidas.", 400)

    repository = ProductRepository()
    if barcode and repository.get_product_by_barcode(barcode):
        return api_error("Já existe um produto com este código de barras.", 400)

    repository.insert_product(
        name=name,
        price=price,
        cost=cost,
        barcode=barcode,
        stock_quantity=stock,
        min_stock=min_stock,
        obs=obs,
    )
    return api_response(_products_payload(), status=201)


@bp.route("/products/<int:product_id>", methods=["PUT"])
@api_login_required
def products_edit(product_id):
    """Atualiza os dados do produto."""
    repository = ProductRepository()
    if not repository.get_product(product_id):
        return api_error("Produto não encontrado.", 404)

    data = request.get_json(silent=True) or {}
    name = (data.get("name") or "").strip()
    price = br_to_decimal(data.get("price"))
    cost = br_to_decimal(data.get("cost"))
    barcode = (data.get("barcode") or "").strip() or None
    obs = (data.get("obs") or "").strip() or None
    active = bool(data.get("active"))

    if not name:
        return api_error("Informe o nome do produto.", 400)
    if price is None or price < 0:
        return api_error("Informe um preço válido.", 400)
    if cost is None or cost < 0:
        return api_error("Informe um custo válido.", 400)

    try:
        min_stock = int(data.get("min_stock") or 0)
    except (TypeError, ValueError):
        return api_error("Estoque mínimo inválido.", 400)
    if min_stock < 0:
        return api_error("Estoque mínimo inválido.", 400)

    existing = repository.get_product_by_barcode(barcode) if barcode else None
    if existing and existing.id != product_id:
        return api_error("Já existe um produto com este código de barras.", 400)

    repository.update_product(
        product_id,
        name=name,
        price=price,
        cost=cost,
        barcode=barcode,
        min_stock=min_stock,
        obs=obs,
        active=active,
    )
    return api_response(_products_payload())


@bp.route("/products/<int:product_id>/adjust", methods=["POST"])
@api_login_required
def products_adjust(product_id):
    """Ajusta o estoque de um produto (delta pode ser negativo)."""
    repository = ProductRepository()
    product = repository.get_product(product_id)
    if not product:
        return api_error("Produto não encontrado.", 404)

    data = request.get_json(silent=True) or {}
    try:
        delta = int(data.get("delta"))
    except (TypeError, ValueError):
        return api_error("Quantidade inválida.", 400)
    if delta == 0:
        return api_error("A quantidade deve ser diferente de zero.", 400)

    obs = (data.get("obs") or "").strip() or None
    new_stock = product.stock_quantity + delta
    if new_stock < 0:
        return api_error(
            f"Estoque insuficiente: o produto tem {product.stock_quantity} unidade(s).",
            400,
        )

    repository.adjust_stock(product_id=product_id, delta=delta, obs=obs)
    return api_response(_products_payload())


@bp.route("/products/<int:product_id>/movements", methods=["GET"])
@api_login_required
def products_movements(product_id):
    """Últimas movimentações de estoque do produto."""
    repository = ProductRepository()
    product = repository.get_product(product_id)
    if not product:
        return api_error("Produto não encontrado.", 404)
    movements = repository.get_movements(product_id, limit=10)
    return api_response(
        {
            "name": product.name,
            "stock_quantity": product.stock_quantity,
            "movements": [_serialize_movement(m) for m in movements],
        }
    )


@bp.route("/products/<int:product_id>", methods=["DELETE"])
@api_login_required
def products_delete(product_id):
    """Exclui um produto que ainda não foi vendido."""
    repository = ProductRepository()
    if not repository.get_product(product_id):
        return api_error("Produto não encontrado.", 404)
    if repository.count_orders(product_id) > 0:
        return api_error(
            "Não é possível excluir: o produto já foi vendido no PDV.", 400
        )
    repository.delete_product(product_id)
    return api_response(_products_payload())
