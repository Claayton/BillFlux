"""File to instantiate the blueprint for the products (catalog) page"""

from decimal import Decimal, InvalidOperation

from flask import flash, redirect, request, url_for
from flask.blueprints import Blueprint
from flask.templating import render_template

from billflux.controlers.auth import login_required
from billflux.infra.repository.product_repository import ProductRepository

bp = Blueprint("bp_products", __name__)


def _parse_br_decimal(value):
    """Converte um valor no formato brasileiro (1.234,56) para Decimal."""
    raw = (value or "").strip()
    if not raw:
        return None
    try:
        if "," in raw:
            return Decimal(raw.replace(".", "").replace(",", "."))
        return Decimal(raw)
    except InvalidOperation:
        return None


@bp.route("/products/", methods=["GET"])
@bp.route("/products", methods=["GET"])
@login_required
def products():
    """Lista o catálogo de produtos."""

    repository = ProductRepository()
    products_list = repository.get_products()
    return render_template(
        "products.html",
        products_list=products_list,
        active="products",
    )


@bp.route("/products/new", methods=["POST"])
@login_required
def new_product():
    """Cria um novo produto."""

    name = (request.form.get("name") or "").strip()
    price = _parse_br_decimal(request.form.get("price"))
    cost = _parse_br_decimal(request.form.get("cost"))
    barcode = (request.form.get("barcode") or "").strip() or None
    stock = request.form.get("stock_quantity")
    min_stock = request.form.get("min_stock")
    obs = (request.form.get("obs") or "").strip() or None

    if not name:
        flash("Informe o nome do produto.", "error")
        return redirect(url_for("bp_products.products"))
    if price is None or price < 0:
        flash("Informe um preço válido.", "error")
        return redirect(url_for("bp_products.products"))
    if cost is None or cost < 0:
        flash("Informe um custo válido.", "error")
        return redirect(url_for("bp_products.products"))

    stock = int(stock) if str(stock).strip().isdigit() else 0
    min_stock = int(min_stock) if str(min_stock).strip().isdigit() else 0
    if stock < 0 or min_stock < 0:
        flash("Quantidades inválidas.", "error")
        return redirect(url_for("bp_products.products"))

    if barcode and ProductRepository().get_product_by_barcode(barcode):
        flash("Já existe um produto com este código de barras.", "error")
        return redirect(url_for("bp_products.products"))

    ProductRepository().insert_product(
        name=name,
        price=price,
        cost=cost,
        barcode=barcode,
        stock_quantity=stock,
        min_stock=min_stock,
        obs=obs,
    )
    flash("Produto criado com sucesso!", "success")
    return redirect(url_for("bp_products.products"))


@bp.route("/products/edit", methods=["POST"])
@login_required
def edit_product():
    """Atualiza os dados de um produto."""

    product_id = request.form.get("product_id")
    name = (request.form.get("name") or "").strip()
    price = _parse_br_decimal(request.form.get("price"))
    cost = _parse_br_decimal(request.form.get("cost"))
    barcode = (request.form.get("barcode") or "").strip() or None
    min_stock = request.form.get("min_stock")
    obs = (request.form.get("obs") or "").strip() or None
    active = request.form.get("active") == "on"

    if not product_id or not product_id.isdigit():
        flash("Produto não encontrado.", "error")
        return redirect(url_for("bp_products.products"))
    if not name:
        flash("Informe o nome do produto.", "error")
        return redirect(url_for("bp_products.products"))
    if price is None or price < 0:
        flash("Informe um preço válido.", "error")
        return redirect(url_for("bp_products.products"))
    if cost is None or cost < 0:
        flash("Informe um custo válido.", "error")
        return redirect(url_for("bp_products.products"))

    min_stock = int(min_stock) if str(min_stock).strip().isdigit() else 0
    if min_stock < 0:
        flash("Quantidade mínima inválida.", "error")
        return redirect(url_for("bp_products.products"))

    repository = ProductRepository()
    existing = repository.get_product_by_barcode(barcode) if barcode else None
    if barcode and existing and existing.id != int(product_id):
        flash("Já existe um produto com este código de barras.", "error")
        return redirect(url_for("bp_products.products"))

    repository.update_product(
        int(product_id),
        name=name,
        price=price,
        cost=cost,
        barcode=barcode,
        min_stock=min_stock,
        obs=obs,
        active=active,
    )
    flash("Produto atualizado com sucesso!", "success")
    return redirect(url_for("bp_products.products"))


@bp.route("/products/adjust", methods=["POST"])
@login_required
def adjust_stock():
    """Ajusta o estoque de um produto (entrada ou saída manual)."""

    product_id = request.form.get("product_id")
    delta = request.form.get("delta")
    obs = (request.form.get("obs") or "").strip() or None

    if not product_id or not product_id.isdigit():
        flash("Produto não encontrado.", "error")
        return redirect(url_for("bp_products.products"))
    if not str(delta).strip().lstrip("-").isdigit() or delta.strip() == "-":
        flash("Informe uma quantidade válida.", "error")
        return redirect(url_for("bp_products.products"))

    delta = int(delta)
    if delta == 0:
        flash("A quantidade não pode ser zero.", "error")
        return redirect(url_for("bp_products.products"))

    result = ProductRepository().adjust_stock(
        int(product_id), delta, obs=obs, movement_type="ajuste"
    )
    if result is None:
        flash("Estoque insuficiente para a saída informada.", "error")
        return redirect(url_for("bp_products.products"))

    flash("Estoque ajustado com sucesso!", "success")
    return redirect(url_for("bp_products.products"))


@bp.route("/products/delete/<int:product_id>", methods=["POST"])
@login_required
def delete_product(product_id):
    """Exclui um produto, desde que não esteja em uso em pedidos."""

    repository = ProductRepository()
    if not repository.get_product(product_id):
        flash("Produto não encontrado.", "error")
        return redirect(url_for("bp_products.products"))
    if repository.count_orders(product_id) > 0:
        flash(
            "Não é possível excluir: o produto já foi vendido.",
            "error",
        )
        return redirect(url_for("bp_products.products"))

    repository.delete_product(product_id)
    flash("Produto excluído.", "success")
    return redirect(url_for("bp_products.products"))


@bp.route("/products/movements/<int:product_id>", methods=["GET"])
@login_required
def product_movements(product_id):
    """Renderiza o fragmento com as movimentações recentes de um produto."""

    repository = ProductRepository()
    product = repository.get_product(product_id)
    if not product:
        return "", 404
    movements = repository.get_movements(product_id)
    return render_template(
        "products_movements.html", product=product, movements=movements
    )
