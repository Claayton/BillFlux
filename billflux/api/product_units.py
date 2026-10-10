"""Endpoints de apresentações de produto (unidade, caixa, etc.)."""

from flask import request

from billflux.api import bp, api_error, api_login_required, api_response, br_to_decimal
from billflux.infra.repository.product_unit_repository import ProductUnitRepository


def _serialize(pu):
    return {
        "id": pu.id,
        "product_id": pu.product_id,
        "name": pu.name,
        "barcode": pu.barcode,
        "factor": pu.factor,
        "price": float(pu.price),
        "is_default": pu.is_default,
    }


@bp.route("/products/<int:product_id>/units", methods=["GET"])
@api_login_required
def list_units(product_id):
    """Lista apresentações de um produto."""
    repo = ProductUnitRepository()
    units = repo.get_units_for_product(product_id)
    return api_response({"units": [_serialize(u) for u in units]})


def _sync_base_price_if_default(repo, product_id, unit):
    """A apresentação padrão de fator 1 é o preço-base do produto.

    Ao cadastrar/editar a "Unidade" (default, fator 1), reflete o preço dela em
    product.price — assim uma caixa/pack (fator > 1) nunca vira o preço-base.
    """
    if unit.is_default and (unit.factor or 1) == 1:
        repo.sync_product_base_price(product_id, unit.price)


@bp.route("/products/<int:product_id>/units", methods=["POST"])
@api_login_required
def create_unit(product_id):
    """Cria uma apresentação para um produto."""
    data = request.get_json(silent=True) or {}
    name = (data.get("name") or "").strip()
    if not name:
        return api_error("Nome é obrigatório.", 400)

    barcode = (data.get("barcode") or "").strip() or None
    factor = int(data.get("factor") or 1)
    is_default = bool(data.get("is_default", False))
    price = br_to_decimal(data.get("price")) or 0

    if factor < 1:
        return api_error("Fator deve ser pelo menos 1.", 400)
    if factor > 1 and is_default:
        return api_error("A apresentação padrão precisa ter fator 1.", 400)

    repo = ProductUnitRepository()
    try:
        unit = repo.upsert(
            product_id=product_id,
            name=name,
            barcode=barcode,
            factor=factor,
            price=price,
            is_default=is_default,
        )
    except ValueError as e:
        return api_error(str(e), 400)

    _sync_base_price_if_default(repo, product_id, unit)
    return api_response({"unit": _serialize(unit)}, status=201)


@bp.route("/product-units/<int:unit_id>", methods=["PUT"])
@api_login_required
def update_unit(unit_id):
    """Atualiza uma apresentação (campos omitidos preservam o valor atual)."""
    data = request.get_json(silent=True) or {}

    repo = ProductUnitRepository()
    current = repo.get_unit(unit_id)
    if not current:
        return api_error("Apresentação não encontrada.", 404)

    name = (data.get("name") or "").strip() or current.name
    barcode = current.barcode
    if "barcode" in data:
        barcode = (data.get("barcode") or "").strip() or None
    factor = int(data.get("factor") or current.factor or 1)
    is_default = bool(data.get("is_default", current.is_default))
    price = br_to_decimal(data.get("price"))
    price = current.price if price is None else price

    if factor < 1:
        return api_error("Fator deve ser pelo menos 1.", 400)
    if factor > 1 and is_default:
        return api_error("A apresentação padrão precisa ter fator 1.", 400)

    try:
        unit = repo.upsert(
            product_id=current.product_id,
            name=name,
            barcode=barcode,
            factor=factor,
            price=price,
            is_default=is_default,
            unit_id=unit_id,
        )
    except ValueError as e:
        return api_error(str(e), 400)

    _sync_base_price_if_default(repo, unit.product_id, unit)
    return api_response({"unit": _serialize(unit)})


@bp.route("/product-units/<int:unit_id>", methods=["DELETE"])
@api_login_required
def delete_unit(unit_id):
    """Remove uma apresentação (não pode remover a padrão)."""
    repo = ProductUnitRepository()
    if repo.delete(unit_id):
        return api_response({"ok": True})
    return api_error("Apresentação não encontrada ou é a padrão.", 400)
