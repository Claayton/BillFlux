"""Endpoints de formas de pagamento da API JSON."""

from flask import request

from billflux.api import bp, api_error, api_login_required, api_response
from billflux.infra.repository.payment_method_repository import (
    PaymentMethodRepository,
)


def _serialize_method(method):
    return {
        "id": method.id,
        "name": method.name,
        "active": method.active,
        "sort_order": method.sort_order,
    }


def _methods_payload():
    return {
        "methods": [
            _serialize_method(m) for m in PaymentMethodRepository().get_methods()
        ]
    }


@bp.route("/payments")
@api_login_required
def payments():
    """Lista as formas de pagamento cadastradas."""
    return api_response(_methods_payload())


@bp.route("/payments", methods=["POST"])
@api_login_required
def payments_create():
    """Cadastra uma nova forma de pagamento."""
    name = (request.get_json(silent=True) or {}).get("name")
    name = (name or "").strip()
    if not name:
        return api_error("Informe o nome da forma de pagamento.", 400)

    repository = PaymentMethodRepository()
    if any(m.name.lower() == name.lower() for m in repository.get_methods()):
        return api_error("Já existe uma forma de pagamento com este nome.", 400)

    repository.insert_method(name=name, sort_order=len(repository.get_methods()))
    return api_response(_methods_payload(), status=201)


@bp.route("/payments/<int:method_id>/toggle", methods=["POST"])
@api_login_required
def payments_toggle(method_id):
    """Ativa ou desativa uma forma de pagamento."""
    repository = PaymentMethodRepository()
    method = repository.get_method(method_id)
    if not method:
        return api_error("Forma de pagamento não encontrada.", 404)

    repository.update_method(method_id, active=not method.active)
    return api_response(_methods_payload())


@bp.route("/payments/<int:method_id>", methods=["DELETE"])
@api_login_required
def payments_delete(method_id):
    """Exclui uma forma de pagamento que ainda não foi usada."""
    repository = PaymentMethodRepository()
    if not repository.get_method(method_id):
        return api_error("Forma de pagamento não encontrada.", 404)
    if repository.count_orders(method_id) > 0:
        return api_error(
            "Não é possível excluir: a forma já foi usada em vendas no PDV.", 400
        )
    repository.delete_method(method_id)
    return api_response(_methods_payload())
