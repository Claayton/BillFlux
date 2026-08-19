"""File to instantiate the blueprint for the PDV (point of sale) page"""

from flask import flash, redirect, request, url_for
from flask.blueprints import Blueprint
from flask.templating import render_template

from billflux.controlers.auth import login_required
from billflux.infra.repository.order_repository import OrderRepository
from billflux.infra.repository.payment_method_repository import PaymentMethodRepository
from billflux.infra.repository.product_repository import ProductRepository

bp = Blueprint("bp_pdv", __name__)


@bp.route("/pdv/", methods=["GET"])
@bp.route("/pdv", methods=["GET"])
@login_required
def pdv():
    """Renderiza o ponto de venda: catálogo + carrinho + formas de pagamento."""

    products_list = ProductRepository().get_active_products()
    methods_list = PaymentMethodRepository().get_active_methods()
    return render_template(
        "pdv.html",
        products_list=products_list,
        methods_list=methods_list,
        active="pdv",
    )


@bp.route("/pdv/complete", methods=["POST"])
@login_required
def complete():
    """Finaliza uma venda: valida e cria o pedido de forma transacional."""

    method_id = request.form.get("payment_method_id")
    obs = (request.form.get("obs") or "").strip() or None

    if not method_id or not method_id.isdigit():
        flash("Selecione a forma de pagamento.", "error")
        return redirect(url_for("bp_pdv.pdv"))

    method = PaymentMethodRepository().get_method(int(method_id))
    if not method or not method.active:
        flash("Forma de pagamento inválida.", "error")
        return redirect(url_for("bp_pdv.pdv"))

    product_ids = request.form.getlist("product_id")
    quantities = request.form.getlist("quantity")
    if not product_ids:
        flash("Adicione ao menos um item ao carrinho.", "error")
        return redirect(url_for("bp_pdv.pdv"))

    items = []
    for product_id, quantity in zip(product_ids, quantities):
        if not product_id.isdigit() or not str(quantity).strip().isdigit():
            continue
        items.append((int(product_id), int(quantity)))

    if not items:
        flash("Adicione ao menos um item ao carrinho.", "error")
        return redirect(url_for("bp_pdv.pdv"))

    try:
        order = OrderRepository().create_order(items, method.id, obs=obs)
    except ValueError as error:
        flash(str(error), "error")
        return redirect(url_for("bp_pdv.pdv"))

    flash(f"Venda #{order.id} finalizada com sucesso!", "success")
    return redirect(url_for("bp_pdv.receipt", order_id=order.id))


@bp.route("/pdv/recibo/<int:order_id>", methods=["GET"])
@login_required
def receipt(order_id):
    """Renderiza o recibo impressível de um pedido."""

    repository = OrderRepository()
    order = repository.get_order(order_id)
    if not order:
        flash("Pedido não encontrado.", "error")
        return redirect(url_for("bp_pdv.pdv"))

    items = repository.get_order_items(order_id)
    method = PaymentMethodRepository().get_method(order.payment_method_id)
    product_names = {}
    for item in items:
        product = ProductRepository().get_product(item.product_id)
        product_names[item.product_id] = product.name if product else "Item"
    return render_template(
        "receipt.html",
        order=order,
        items=items,
        method=method,
        product_names=product_names,
        active="pdv",
    )
