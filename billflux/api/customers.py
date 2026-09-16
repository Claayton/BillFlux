"""Endpoints de clientes da API JSON."""

from flask import request

from billflux.api import bp, api_error, api_login_required, api_response
from billflux.infra.repository.customer_repository import CustomerRepository
from billflux.infra.repository.order_repository import OrderRepository
from billflux.infra.repository.payment_method_repository import (
    PaymentMethodRepository,
)


def _serialize(c):
    return {
        "id": c.id,
        "name": c.name,
        "cpf_cnpj": c.cpf_cnpj or "",
        "phone": c.phone or "",
        "email": c.email or "",
        "address": c.address or "",
        "city": c.city or "",
        "state": c.state or "",
        "neighborhood": c.neighborhood or "",
        "complement": c.complement or "",
        "number": c.number or "",
        "zip_code": c.zip_code or "",
        "obs": c.obs or "",
        "active": c.active,
    }


def _customers_payload():
    repository = CustomerRepository()
    search = request.args.get("search", "").strip() or None
    customers = repository.get_customers(search=search)
    return {
        "customers": [_serialize(c) for c in customers],
    }


@bp.route("/customers")
@api_login_required
def customers():
    """Lista os clientes cadastrados."""
    return api_response(_customers_payload())


@bp.route("/customers", methods=["POST"])
@api_login_required
def customers_create():
    """Cadastra um novo cliente."""
    data = request.get_json(silent=True) or {}
    name = (data.get("name") or "").strip()
    if not name:
        return api_error("Informe o nome do cliente.", 400)

    cpf_cnpj = (data.get("cpf_cnpj") or "").strip() or None
    if cpf_cnpj:
        repository = CustomerRepository()
        existing = repository.get_customer_by_cpf_cnpj(cpf_cnpj)
        if existing:
            return api_error("Já existe um cliente com este CPF/CNPJ.", 400)

    fields = {
        "name": name,
        "cpf_cnpj": cpf_cnpj,
        "phone": (data.get("phone") or "").strip() or None,
        "email": (data.get("email") or "").strip() or None,
        "address": (data.get("address") or "").strip() or None,
        "city": (data.get("city") or "").strip() or None,
        "state": (data.get("state") or "").strip() or None,
        "neighborhood": (data.get("neighborhood") or "").strip() or None,
        "complement": (data.get("complement") or "").strip() or None,
        "number": (data.get("number") or "").strip() or None,
        "zip_code": (data.get("zip_code") or "").strip() or None,
        "obs": (data.get("obs") or "").strip() or None,
    }

    repository = CustomerRepository()
    repository.insert_customer(**fields)
    return api_response(_customers_payload(), status=201)


@bp.route("/customers/<int:customer_id>", methods=["PUT"])
@api_login_required
def customers_update(customer_id):
    """Atualiza um cliente existente."""
    repository = CustomerRepository()
    customer = repository.get_customer(customer_id)
    if not customer:
        return api_error("Cliente não encontrado.", 404)

    data = request.get_json(silent=True) or {}
    name = (data.get("name") or "").strip()
    if not name:
        return api_error("Informe o nome do cliente.", 400)

    cpf_cnpj = (data.get("cpf_cnpj") or "").strip() or None
    if cpf_cnpj:
        existing = repository.get_customer_by_cpf_cnpj(cpf_cnpj)
        if existing and existing.id != customer_id:
            return api_error("Já existe um cliente com este CPF/CNPJ.", 400)

    fields = {
        "name": name,
        "cpf_cnpj": cpf_cnpj,
        "phone": (data.get("phone") or "").strip() or None,
        "email": (data.get("email") or "").strip() or None,
        "address": (data.get("address") or "").strip() or None,
        "city": (data.get("city") or "").strip() or None,
        "state": (data.get("state") or "").strip() or None,
        "neighborhood": (data.get("neighborhood") or "").strip() or None,
        "complement": (data.get("complement") or "").strip() or None,
        "number": (data.get("number") or "").strip() or None,
        "zip_code": (data.get("zip_code") or "").strip() or None,
        "obs": (data.get("obs") or "").strip() or None,
        "active": data.get("active", customer.active),
    }

    repository.update_customer(customer_id, **fields)
    return api_response(_customers_payload())


@bp.route("/customers/<int:customer_id>/toggle", methods=["POST"])
@api_login_required
def customers_toggle(customer_id):
    """Ativa ou desativa um cliente."""
    repository = CustomerRepository()
    customer = repository.get_customer(customer_id)
    if not customer:
        return api_error("Cliente não encontrado.", 404)
    repository.toggle_active(customer_id)
    return api_response(_customers_payload())


@bp.route("/customers/<int:customer_id>", methods=["DELETE"])
@api_login_required
def customers_delete(customer_id):
    """Exclui um cliente."""
    repository = CustomerRepository()
    if not repository.get_customer(customer_id):
        return api_error("Cliente não encontrado.", 404)
    repository.delete_customer(customer_id)
    return api_response(_customers_payload())


@bp.route("/customers/<int:customer_id>/orders")
@api_login_required
def customer_orders(customer_id):
    """Lista os pedidos de um cliente."""
    repository = CustomerRepository()
    customer = repository.get_customer(customer_id)
    if not customer:
        return api_error("Cliente não encontrado.", 404)

    order_repo = OrderRepository()
    method_repo = PaymentMethodRepository()
    orders = order_repo.get_orders_by_customer(customer_id)

    result = []
    for order in orders:
        method = method_repo.get_method(order.payment_method_id)
        result.append({
            "order_id": order.id,
            "date": order.created_at.isoformat(),
            "total": float(order.total),
            "discount": float(order.discount or 0),
            "payment_method": method.name if method else "—",
            "cancelled": order.cancelled,
        })

    return api_response({
        "customer": _serialize(customer),
        "orders": result,
        "total_spent": sum(o["total"] for o in result if not o["cancelled"]),
        "order_count": len([o for o in result if not o["cancelled"]]),
    })
