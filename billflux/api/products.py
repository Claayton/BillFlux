"""Endpoints de produtos (catálogo e estoque) da API JSON."""

from flask import request

from billflux.api import bp, api_error, api_login_required, api_response, br_to_decimal
from billflux.infra.repository.category_repository import CategoryRepository
from billflux.infra.repository.product_repository import ProductRepository
from billflux.infra.repository.supplier_repository import SupplierRepository
from billflux.infra.repository.product_unit_repository import ProductUnitRepository


def _parse_category_id(data):
    """Lê e valida o category_id (None quando ausente)."""
    raw = data.get("category_id")
    if raw is None or raw == "":
        return None
    try:
        category_id = int(raw)
    except (TypeError, ValueError):
        return None
    category = CategoryRepository().get_category(category_id)
    return category.id if category else None


def _parse_supplier_id(data):
    """Lê e valida o supplier_id (None quando ausente)."""
    raw = data.get("supplier_id")
    if raw is None or raw == "":
        return None
    try:
        supplier_id = int(raw)
    except (TypeError, ValueError):
        return None
    supplier = SupplierRepository().get_supplier(supplier_id)
    return supplier.id if supplier else None


def _serialize_product(product, units=None):
    data = {
        "id": product.id,
        "name": product.name,
        "price": float(product.price),
        "cost": float(product.cost),
        "barcode": product.barcode,
        "secondary_code": product.secondary_code,
        "category_id": product.category_id,
        "category_name": product.category_name,
        "suppliers": product.suppliers,
        "supplier_id": product.supplier_id,
        "supplier_name": product.supplier_name,
        "stock_quantity": product.stock_quantity,
        "min_stock": product.min_stock,
        "ideal_stock": getattr(product, "ideal_stock", 0) or 0,
        "obs": product.obs,
        "active": product.active,
    }
    if units is not None:
        data["units"] = [
            {
                "id": u.id,
                "product_id": u.product_id,
                "name": u.name,
                "barcode": u.barcode,
                "factor": u.factor,
                "price": float(u.price),
                "is_default": u.is_default,
            }
            for u in units
        ]
    return data


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
    unit_repo = ProductUnitRepository()
    suppliers = SupplierRepository().get_suppliers(active_only=True)
    products = repository.get_products()
    product_ids = [p.id for p in products]
    all_units = unit_repo.get_units_for_products(product_ids)
    units_by_product = {}
    for u in all_units:
        units_by_product.setdefault(u.product_id, []).append(u)
    return {
        "products": [
            _serialize_product(p, units_by_product.get(p.id)) for p in products
        ],
        "suppliers": [{"id": s.id, "name": s.name} for s in suppliers],
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
    secondary_code = (data.get("secondary_code") or "").strip() or None
    category_id = _parse_category_id(data)
    suppliers = (data.get("suppliers") or "").strip() or None
    supplier_id = _parse_supplier_id(data)
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
        ideal_stock = int(data.get("ideal_stock") or 0)
    except (TypeError, ValueError):
        return api_error("Quantidades invalidas.", 400)
    if stock < 0 or min_stock < 0 or ideal_stock < 0:
        return api_error("Quantidades invalidas.", 400)

    repository = ProductRepository()
    if barcode and repository.get_product_by_barcode(barcode):
        return api_error("Já existe um produto com este código de barras.", 400)

    repository.insert_product(
        name=name,
        price=price,
        cost=cost,
        barcode=barcode,
        secondary_code=secondary_code,
        category_id=category_id,
        suppliers=suppliers,
        supplier_id=supplier_id,
        stock_quantity=stock,
        min_stock=min_stock,
        ideal_stock=ideal_stock,
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
    secondary_code = (data.get("secondary_code") or "").strip() or None
    category_id = _parse_category_id(data)
    suppliers = (data.get("suppliers") or "").strip() or None
    supplier_id = _parse_supplier_id(data)
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
        ideal_stock = int(data.get("ideal_stock") or 0)
    except (TypeError, ValueError):
        return api_error("Estoque invalido.", 400)
    if min_stock < 0 or ideal_stock < 0:
        return api_error("Estoque invalido.", 400)

    existing = repository.get_product_by_barcode(barcode) if barcode else None
    if existing and existing.id != product_id:
        return api_error("Já existe um produto com este código de barras.", 400)

    repository.update_product(
        product_id,
        name=name,
        price=price,
        cost=cost,
        barcode=barcode,
        secondary_code=secondary_code,
        category_id=category_id,
        suppliers=suppliers,
        supplier_id=supplier_id,
        min_stock=min_stock,
        ideal_stock=ideal_stock,
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


@bp.route("/products/barcode/<barcode>")
@api_login_required
def products_by_barcode(barcode):
    """Busca um produto pelo código de barras (produto ou apresentação)."""
    repository = ProductRepository()
    unit_repo = ProductUnitRepository()

    product = repository.get_product_by_barcode(barcode)
    if product:
        units = unit_repo.get_units_for_product(product.id)
        return api_response({"product": _serialize_product(product, units)})

    unit = unit_repo.get_unit_by_barcode(barcode)
    if unit:
        product = repository.get_product(unit.product_id)
        if product:
            units = unit_repo.get_units_for_product(product.id)
            return api_response({"product": _serialize_product(product, units)})

    return api_error("Produto não encontrado.", 404)


@bp.route("/products/search")
@api_login_required
def products_search():
    """Busca produtos por nome (parcial), sem considerar acentos.
    Também busca por código de barras de apresentação."""
    from billflux.services.text_normalize import strip_accents

    q = request.args.get("q", "").strip()
    if not q:
        return api_response({"products": []})
    repository = ProductRepository()
    unit_repo = ProductUnitRepository()
    all_products = repository.get_active_products()
    like = strip_accents(q).lower()

    matches = [
        p
        for p in all_products
        if like in strip_accents(p.name or "").lower()
        or like == (p.barcode or "").lower()
    ]

    if not matches:
        unit = unit_repo.get_unit_by_barcode(q)
        if unit:
            p = repository.get_product(unit.product_id)
            if p and p.active:
                matches = [p]

    matches = matches[:20]
    product_ids = [p.id for p in matches]
    all_units = unit_repo.get_units_for_products(product_ids)
    units_by_product = {}
    for u in all_units:
        units_by_product.setdefault(u.product_id, []).append(u)
    return api_response(
        {
            "products": [
                _serialize_product(p, units_by_product.get(p.id)) for p in matches
            ]
        }
    )


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
