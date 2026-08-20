"""Endpoints do plano de contas (categorias) da API JSON."""

from flask import request

from billflux.api import bp, api_error, api_login_required, api_response
from billflux.infra.repository.account_repository import AccountRepository

ACCOUNT_TYPES = ("receita", "despesa")


def _build_tree(accounts):
    """Organiza as contas em árvore (2 níveis) para a listagem."""
    children = {}
    for account in accounts:
        if account.parent_id:
            children.setdefault(account.parent_id, []).append(account)

    tree = []
    for account in accounts:
        if not account.parent_id:
            tree.append(
                {
                    "account": account,
                    "children": sorted(
                        children.get(account.id, []), key=lambda a: a.name.lower()
                    ),
                }
            )
    return sorted(tree, key=lambda g: g["account"].name.lower())


def _serialize_account(account):
    return {
        "id": account.id,
        "name": account.name,
        "type": account.type,
        "parent_id": account.parent_id,
        "color": account.color,
        "active": account.active,
    }


def _sections(accounts_list):
    sections = []
    for type_label, type_key in (("Receitas", "receita"), ("Despesas", "despesa")):
        groups = [
            {
                "account": _serialize_account(group["account"]),
                "children": [_serialize_account(c) for c in group["children"]],
            }
            for group in _build_tree(accounts_list)
            if group["account"].type == type_key
        ]
        sections.append({"label": type_label, "type": type_key, "groups": groups})
    return sections


def _accounts_payload():
    return {"sections": _sections(AccountRepository().get_accounts())}


@bp.route("/accounts")
@api_login_required
def accounts():
    """Lista o plano de contas organizado por tipo e subcategorias."""
    return api_response(_accounts_payload())


@bp.route("/accounts", methods=["POST"])
@api_login_required
def accounts_create():
    """Cria uma nova categoria (pai ou subcategoria)."""
    data = request.get_json(silent=True) or {}
    name = (data.get("name") or "").strip()
    type_ = data.get("type")
    parent_id = data.get("parent_id")
    color = (data.get("color") or "").strip() or None

    if not name:
        return api_error("Informe o nome da categoria.", 400)
    if type_ not in ACCOUNT_TYPES:
        return api_error("Tipo de categoria inválido.", 400)

    try:
        parent_id = int(parent_id) if parent_id else None
    except (TypeError, ValueError):
        return api_error("Categoria pai inválida.", 400)

    AccountRepository().insert_account(
        name=name, type=type_, parent_id=parent_id, color=color
    )
    return api_response(_accounts_payload(), status=201)


@bp.route("/accounts/<int:account_id>", methods=["PUT"])
@api_login_required
def accounts_edit(account_id):
    """Atualiza o nome, tipo, cor ou pai de uma categoria."""
    repository = AccountRepository()
    if not repository.get_account(account_id):
        return api_error("Categoria não encontrada.", 404)

    data = request.get_json(silent=True) or {}
    name = (data.get("name") or "").strip()
    type_ = data.get("type")
    parent_id = data.get("parent_id")
    color = (data.get("color") or "").strip() or None

    if not name:
        return api_error("Informe o nome da categoria.", 400)
    if type_ not in ACCOUNT_TYPES:
        return api_error("Tipo de categoria inválido.", 400)

    try:
        parent_id = int(parent_id) if parent_id else None
    except (TypeError, ValueError):
        return api_error("Categoria pai inválida.", 400)
    if parent_id == account_id:
        return api_error("Uma categoria não pode ser subcategoria dela mesma.", 400)

    repository.update_account(
        account_id, name=name, type=type_, parent_id=parent_id, color=color
    )
    return api_response(_accounts_payload())


@bp.route("/accounts/<int:account_id>", methods=["DELETE"])
@api_login_required
def accounts_delete(account_id):
    """Exclui uma categoria sem subcategorias nem contas vinculadas."""
    repository = AccountRepository()
    if not repository.get_account(account_id):
        return api_error("Categoria não encontrada.", 404)
    if repository.count_children(account_id) > 0:
        return api_error(
            "Não é possível excluir: a categoria possui subcategorias.", 400
        )
    if repository.count_bills(account_id) > 0:
        return api_error(
            "Não é possível excluir: há contas vinculadas a esta categoria.", 400
        )
    repository.delete_account(account_id)
    return api_response(_accounts_payload())
