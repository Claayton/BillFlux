"""File to instantiate the blueprint for the chart of accounts page"""

from flask import flash, redirect, request, url_for
from flask.blueprints import Blueprint
from flask.templating import render_template

from billflux.controlers.auth import login_required
from billflux.infra.repository.account_repository import AccountRepository

bp = Blueprint("bp_accounts", __name__)

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


@bp.route("/accounts/", methods=["GET"])
@bp.route("/accounts", methods=["GET"])
@login_required
def accounts():
    """Lista as categorias do plano de contas."""

    repository = AccountRepository()
    accounts_list = repository.get_accounts()

    sections = []
    for type_label, type_key in (("Receitas", "receita"), ("Despesas", "despesa")):
        groups = [
            group
            for group in _build_tree(accounts_list)
            if group["account"].type == type_key
        ]
        sections.append({"label": type_label, "type": type_key, "groups": groups})

    return render_template(
        "accounts.html",
        sections=sections,
        accounts_list=accounts_list,
        active="accounts",
    )


@bp.route("/accounts/new", methods=["POST"])
@login_required
def new_account():
    """Cria uma nova categoria no plano de contas."""

    name = (request.form.get("name") or "").strip()
    type_ = request.form.get("type")
    parent_id = request.form.get("parent_id")
    color = (request.form.get("color") or "").strip() or None

    if not name:
        flash("Informe o nome da categoria.", "error")
        return redirect(url_for("bp_accounts.accounts"))
    if type_ not in ACCOUNT_TYPES:
        flash("Tipo de categoria inválido.", "error")
        return redirect(url_for("bp_accounts.accounts"))

    parent_id = int(parent_id) if parent_id else None
    AccountRepository().insert_account(
        name=name, type=type_, parent_id=parent_id, color=color
    )
    flash("Categoria criada com sucesso!", "success")
    return redirect(url_for("bp_accounts.accounts"))


@bp.route("/accounts/edit", methods=["POST"])
@login_required
def edit_account():
    """Atualiza uma categoria existente."""

    account_id = request.form.get("account_id")
    name = (request.form.get("name") or "").strip()
    type_ = request.form.get("type")
    parent_id = request.form.get("parent_id")
    color = (request.form.get("color") or "").strip() or None

    if not account_id:
        flash("Categoria não encontrada.", "error")
        return redirect(url_for("bp_accounts.accounts"))
    if not name:
        flash("Informe o nome da categoria.", "error")
        return redirect(url_for("bp_accounts.accounts"))
    if type_ not in ACCOUNT_TYPES:
        flash("Tipo de categoria inválido.", "error")
        return redirect(url_for("bp_accounts.accounts"))

    account_id = int(account_id)
    parent_id = int(parent_id) if parent_id else None
    if parent_id == account_id:
        flash("Uma categoria não pode ser subcategoria dela mesma.", "error")
        return redirect(url_for("bp_accounts.accounts"))

    AccountRepository().update_account(
        account_id,
        name=name,
        type=type_,
        parent_id=parent_id,
        color=color,
    )
    flash("Categoria atualizada com sucesso!", "success")
    return redirect(url_for("bp_accounts.accounts"))


@bp.route("/accounts/delete/<int:account_id>", methods=["POST"])
@login_required
def delete_account(account_id):
    """Exclui uma categoria, desde que não esteja em uso."""

    repository = AccountRepository()
    if not repository.get_account(account_id):
        flash("Categoria não encontrada.", "error")
        return redirect(url_for("bp_accounts.accounts"))
    if repository.count_children(account_id) > 0:
        flash(
            "Não é possível excluir: a categoria possui subcategorias.",
            "error",
        )
        return redirect(url_for("bp_accounts.accounts"))
    if repository.count_bills(account_id) > 0:
        flash(
            "Não é possível excluir: há contas vinculadas a esta categoria.",
            "error",
        )
        return redirect(url_for("bp_accounts.accounts"))

    repository.delete_account(account_id)
    flash("Categoria excluída.", "success")
    return redirect(url_for("bp_accounts.accounts"))
