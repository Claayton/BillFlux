"""Endpoints do PDV (ponto de venda) da API JSON."""

from decimal import Decimal

from flask import request

from billflux.api import (
    bp,
    api_error,
    api_login_required,
    api_response,
    br_to_decimal,
)
from billflux.infra.repository.order_repository import OrderRepository
from billflux.infra.repository.payment_method_repository import (
    PaymentMethodRepository,
)
from billflux.infra.repository.product_repository import ProductRepository


def _serialize_product(product):
    return {
        "id": product.id,
        "name": product.name,
        "price": float(product.price),
        "stock": product.stock_quantity,
        "barcode": product.barcode or "",
    }


def _serialize_method(method):
    return {"id": method.id, "name": method.name}


def _build_receipt(order_id):
    """Monta os dados do recibo de um pedido (ou None se não existir)."""
    repository = OrderRepository()
    order = repository.get_order(order_id)
    if not order:
        return None

    method_repository = PaymentMethodRepository()
    method = method_repository.get_method(order.payment_method_id)
    items_detail = repository.get_order_items(order.id)
    products = {}
    for item in items_detail:
        product = ProductRepository().get_product(item.product_id)
        products[item.product_id] = product.name if product else "Item"

    payments_detail = []
    received_total = Decimal("0")
    for payment_method_id, amount in repository.get_order_payments(order.id):
        received_total += amount
        payment_method = method_repository.get_method(payment_method_id)
        payments_detail.append(
            {
                "method_id": payment_method_id,
                "name": payment_method.name if payment_method else "—",
                "amount": float(amount),
            }
        )

    troco = max(Decimal("0"), received_total - order.total)

    return {
        "order_id": order.id,
        "date": order.created_at.isoformat(),
        "total": float(order.total),
        "discount": float(order.discount or 0),
        "obs": order.obs,
        "payment_method": method.name if method else "—",
        "payments": payments_detail,
        "troco": float(troco),
        "items": [
            {
                "name": products[item.product_id],
                "quantity": item.quantity,
                "unit_price": float(item.unit_price),
                "subtotal": float(item.unit_price) * item.quantity,
            }
            for item in items_detail
        ],
    }


@bp.route("/pdv")
@api_login_required
def pdv():
    """Produtos ativos e formas de pagamento para o ponto de venda."""
    return api_response(
        {
            "products": [
                _serialize_product(p) for p in ProductRepository().get_active_products()
            ],
            "methods": [
                _serialize_method(m)
                for m in PaymentMethodRepository().get_active_methods()
            ],
        }
    )


@bp.route("/pdv/complete", methods=["POST"])
@api_login_required
def complete():
    """Finaliza uma venda e devolve o recibo do pedido criado."""
    data = request.get_json(silent=True) or {}

    method_id = None
    payments = None
    raw_payments = data.get("payments")
    method_repository = PaymentMethodRepository()
    if isinstance(raw_payments, list) and raw_payments:
        payments = []
        for entry in raw_payments:
            try:
                entry_method_id = int(entry.get("method_id"))
                amount = br_to_decimal(entry.get("amount"))
            except (TypeError, ValueError):
                return api_error("Forma de pagamento inválida.", 400)
            if amount is None or amount <= 0:
                return api_error("Valor de pagamento inválido.", 400)
            payment_method = method_repository.get_method(entry_method_id)
            if not payment_method or not payment_method.active:
                return api_error("Selecione a forma de pagamento.", 400)
            payments.append((entry_method_id, amount))
    else:
        try:
            method_id = int(data.get("method_id")) if data.get("method_id") else None
        except (TypeError, ValueError):
            method_id = None
        payment_method = method_repository.get_method(method_id) if method_id else None
        if not payment_method or not payment_method.active:
            return api_error("Selecione a forma de pagamento.", 400)

    items = data.get("items") or []
    if not isinstance(items, list) or not items:
        return api_error("Adicione ao menos um item ao carrinho.", 400)

    cart = []
    for item in items:
        try:
            product_id = int(item.get("product_id"))
            quantity = int(item.get("quantity"))
        except (TypeError, ValueError):
            continue
        if quantity > 0:
            cart.append((product_id, quantity))

    if not cart:
        return api_error("Adicione ao menos um item ao carrinho.", 400)

    obs = (data.get("obs") or "").strip() or None

    discount = br_to_decimal(data.get("discount"))
    if discount is None:
        discount = Decimal("0")
    if discount < 0:
        return api_error("Desconto inválido.", 400)

    repository = OrderRepository()
    try:
        order = repository.create_order(
            cart,
            method_id,
            obs=obs,
            discount=discount,
            payments=payments,
        )
    except ValueError as error:
        return api_error(str(error), 400)

    receipt = _build_receipt(order.id)
    return api_response({"order": receipt}, status=201)


@bp.route("/pdv/recibo/<int:order_id>", methods=["GET"])
@api_login_required
def receipt(order_id):
    """Dados do recibo de um pedido finalizado."""
    receipt_data = _build_receipt(order_id)
    if not receipt_data:
        return api_error("Pedido não encontrado.", 404)
    return api_response({"order": receipt_data})
