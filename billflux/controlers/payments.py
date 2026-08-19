"""File to instantiate the blueprint for the payment methods page"""

from flask import flash, redirect, request, url_for
from flask.blueprints import Blueprint
from flask.templating import render_template

from billflux.controlers.auth import login_required
from billflux.infra.repository.payment_method_repository import PaymentMethodRepository

bp = Blueprint("bp_payments", __name__)


@bp.route("/payments/", methods=["GET"])
@bp.route("/payments", methods=["GET"])
@login_required
def payments():
    """Lista as formas de pagamento configuradas."""

    repository = PaymentMethodRepository()
    methods_list = repository.get_methods()
    return render_template(
        "payments.html",
        methods_list=methods_list,
        active="payments",
    )


@bp.route("/payments/new", methods=["POST"])
@login_required
def new_method():
    """Cria uma nova forma de pagamento."""

    name = (request.form.get("name") or "").strip()
    if not name:
        flash("Informe o nome da forma de pagamento.", "error")
        return redirect(url_for("bp_payments.payments"))

    repository = PaymentMethodRepository()
    duplicate = [m for m in repository.get_methods() if m.name.lower() == name.lower()]
    if duplicate:
        flash("Já existe uma forma de pagamento com este nome.", "error")
        return redirect(url_for("bp_payments.payments"))

    repository.insert_method(name=name, sort_order=len(repository.get_methods()))
    flash("Forma de pagamento criada!", "success")
    return redirect(url_for("bp_payments.payments"))


@bp.route("/payments/toggle/<int:method_id>", methods=["POST"])
@login_required
def toggle_method(method_id):
    """Ativa ou desativa uma forma de pagamento."""

    repository = PaymentMethodRepository()
    method = repository.get_method(method_id)
    if not method:
        flash("Forma de pagamento não encontrada.", "error")
        return redirect(url_for("bp_payments.payments"))

    repository.update_method(method_id, active=not method.active)
    action = "ativada" if not method.active else "desativada"
    flash(f"Forma de pagamento {action}.", "success")
    return redirect(url_for("bp_payments.payments"))


@bp.route("/payments/delete/<int:method_id>", methods=["POST"])
@login_required
def delete_method(method_id):
    """Exclui uma forma de pagamento, desde que não esteja em uso."""

    repository = PaymentMethodRepository()
    if not repository.get_method(method_id):
        flash("Forma de pagamento não encontrada.", "error")
        return redirect(url_for("bp_payments.payments"))
    if repository.count_orders(method_id) > 0:
        flash(
            "Não é possível excluir: a forma de pagamento já foi usada em vendas.",
            "error",
        )
        return redirect(url_for("bp_payments.payments"))

    repository.delete_method(method_id)
    flash("Forma de pagamento excluída.", "success")
    return redirect(url_for("bp_payments.payments"))
