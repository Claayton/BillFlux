"""Endpoints de fornecedores da API JSON."""

from flask import request

from billflux.api import bp, api_error, api_login_required, api_response
from billflux.infra.repository.supplier_repository import SupplierRepository


def _serialize(s):
    return {
        "id": s.id,
        "name": s.name,
        "cnpj": s.cnpj or "",
        "phone": s.phone or "",
        "email": s.email or "",
        "contact": s.contact or "",
        "address": s.address or "",
        "city": s.city or "",
        "state": s.state or "",
        "neighborhood": s.neighborhood or "",
        "obs": s.obs or "",
        "active": s.active,
    }


def _suppliers_payload():
    repository = SupplierRepository()
    search = request.args.get("search", "").strip() or None
    suppliers = repository.get_suppliers(search=search)
    return {
        "suppliers": [_serialize(s) for s in suppliers],
    }


@bp.route("/suppliers")
@api_login_required
def suppliers():
    """Lista os fornecedores cadastrados."""
    return api_response(_suppliers_payload())


@bp.route("/suppliers", methods=["POST"])
@api_login_required
def suppliers_create():
    """Cadastra um novo fornecedor."""
    data = request.get_json(silent=True) or {}
    name = (data.get("name") or "").strip()
    if not name:
        return api_error("Informe o nome do fornecedor.", 400)

    cnpj = (data.get("cnpj") or "").strip() or None
    if cnpj:
        repository = SupplierRepository()
        existing = repository.get_supplier_by_cnpj(cnpj)
        if existing:
            return api_error("Já existe um fornecedor com este CNPJ.", 400)

    fields = {
        "name": name,
        "cnpj": cnpj,
        "phone": (data.get("phone") or "").strip() or None,
        "email": (data.get("email") or "").strip() or None,
        "contact": (data.get("contact") or "").strip() or None,
        "address": (data.get("address") or "").strip() or None,
        "city": (data.get("city") or "").strip() or None,
        "state": (data.get("state") or "").strip() or None,
        "neighborhood": (data.get("neighborhood") or "").strip() or None,
        "obs": (data.get("obs") or "").strip() or None,
    }

    repository = SupplierRepository()
    repository.insert_supplier(**fields)
    return api_response(_suppliers_payload(), status=201)


@bp.route("/suppliers/<int:supplier_id>", methods=["PUT"])
@api_login_required
def suppliers_update(supplier_id):
    """Atualiza um fornecedor existente."""
    repository = SupplierRepository()
    supplier = repository.get_supplier(supplier_id)
    if not supplier:
        return api_error("Fornecedor não encontrado.", 404)

    data = request.get_json(silent=True) or {}
    name = (data.get("name") or "").strip()
    if not name:
        return api_error("Informe o nome do fornecedor.", 400)

    cnpj = (data.get("cnpj") or "").strip() or None
    if cnpj:
        existing = repository.get_supplier_by_cnpj(cnpj)
        if existing and existing.id != supplier_id:
            return api_error("Já existe um fornecedor com este CNPJ.", 400)

    fields = {
        "name": name,
        "cnpj": cnpj,
        "phone": (data.get("phone") or "").strip() or None,
        "email": (data.get("email") or "").strip() or None,
        "contact": (data.get("contact") or "").strip() or None,
        "address": (data.get("address") or "").strip() or None,
        "city": (data.get("city") or "").strip() or None,
        "state": (data.get("state") or "").strip() or None,
        "neighborhood": (data.get("neighborhood") or "").strip() or None,
        "obs": (data.get("obs") or "").strip() or None,
        "active": data.get("active", supplier.active),
    }

    repository.update_supplier(supplier_id, **fields)
    return api_response(_suppliers_payload())


@bp.route("/suppliers/<int:supplier_id>/toggle", methods=["POST"])
@api_login_required
def suppliers_toggle(supplier_id):
    """Ativa ou desativa um fornecedor."""
    repository = SupplierRepository()
    supplier = repository.get_supplier(supplier_id)
    if not supplier:
        return api_error("Fornecedor não encontrado.", 404)
    repository.toggle_active(supplier_id)
    return api_response(_suppliers_payload())


@bp.route("/suppliers/<int:supplier_id>", methods=["DELETE"])
@api_login_required
def suppliers_delete(supplier_id):
    """Exclui um fornecedor."""
    repository = SupplierRepository()
    if not repository.get_supplier(supplier_id):
        return api_error("Fornecedor não encontrado.", 404)
    repository.delete_supplier(supplier_id)
    return api_response(_suppliers_payload())
