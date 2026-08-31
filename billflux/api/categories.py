"""Endpoints de categorias de produtos da API JSON."""

from flask import request

from billflux.api import bp, api_error, api_login_required, api_response
from billflux.infra.repository.category_repository import CategoryRepository
from billflux.infra.repository.product_repository import ProductRepository


def _categories_payload():
    repository = CategoryRepository()
    product_repository = ProductRepository()
    products = product_repository.get_active_products()
    counts = {}
    for product in products:
        if product.category_id:
            counts[product.category_id] = counts.get(product.category_id, 0) + 1
    return {
        "categories": [
            {
                "id": category.id,
                "name": category.name,
                "active": category.active,
                "product_count": counts.get(category.id, 0),
            }
            for category in repository.get_categories()
        ]
    }


@bp.route("/categories")
@api_login_required
def categories():
    """Lista as categorias cadastradas."""
    return api_response(_categories_payload())


@bp.route("/categories", methods=["POST"])
@api_login_required
def categories_create():
    """Cadastra uma nova categoria."""
    name = (request.get_json(silent=True) or {}).get("name")
    name = (name or "").strip()
    if not name:
        return api_error("Informe o nome da categoria.", 400)

    repository = CategoryRepository()
    if any(c.name.lower() == name.lower() for c in repository.get_categories()):
        return api_error("Já existe uma categoria com este nome.", 400)

    repository.insert_category(name=name)
    return api_response(_categories_payload(), status=201)


@bp.route("/categories/<int:category_id>/toggle", methods=["POST"])
@api_login_required
def categories_toggle(category_id):
    """Ativa ou desativa uma categoria."""
    repository = CategoryRepository()
    category = repository.get_category(category_id)
    if not category:
        return api_error("Categoria não encontrada.", 404)

    repository.update_category(category_id, active=not category.active)
    return api_response(_categories_payload())


@bp.route("/categories/<int:category_id>", methods=["DELETE"])
@api_login_required
def categories_delete(category_id):
    """Exclui uma categoria sem produtos vinculados."""
    repository = CategoryRepository()
    if not repository.get_category(category_id):
        return api_error("Categoria não encontrada.", 404)
    if repository.count_products(category_id) > 0:
        return api_error(
            "Não é possível excluir: a categoria tem produtos vinculados. "
            "Remova a categoria dos produtos ou desative-a.",
            400,
        )
    repository.delete_category(category_id)
    return api_response(_categories_payload())
