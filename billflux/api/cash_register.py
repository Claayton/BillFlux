"""Endpoints de caixa (abertura/fechamento) da API JSON."""

import json
from datetime import datetime

from flask import session, request

from billflux.api import bp, api_error, api_login_required, api_response
from billflux.infra.repository.cash_register_repository import CashRegisterRepository
from billflux.infra.repository.payment_method_repository import (
    PaymentMethodRepository,
)


def _serialize(cr):
    return {
        "id": cr.id,
        "opened_by": cr.opened_by,
        "opened_at": cr.opened_at,
        "opening_amount": cr.opening_amount,
        "closed_by": cr.closed_by,
        "closed_at": cr.closed_at,
        "closing_amount": cr.closing_amount,
        "expected_amount": cr.expected_amount,
        "status": cr.status,
        "obs": cr.obs,
        "opening_details": json.loads(cr.opening_details) if cr.opening_details else {},
        "system_totals": json.loads(cr.system_totals) if cr.system_totals else {},
        "closing_details": json.loads(cr.closing_details) if cr.closing_details else {},
    }


def _payment_methods_map():
    """Dict id -> name das formas de pagamento ativas."""
    return {
        m.id: m.name
        for m in PaymentMethodRepository().get_active_methods()
    }


def _caixa_payload():
    repository = CashRegisterRepository()
    open_register = repository.get_open()
    last_closed = repository.get_last_closed()
    history = repository.get_history(limit=20)

    system_totals = {}
    system_totals_named = {}
    if open_register:
        now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        system_totals = repository.compute_system_totals(
            open_register.opened_at, now_str
        )
        methods = _payment_methods_map()
        for mid, total in system_totals.items():
            system_totals_named[mid] = {
                "method_id": int(mid),
                "name": methods.get(int(mid), f"Forma {mid}"),
                "total": total,
            }

    return {
        "open": _serialize(open_register) if open_register else None,
        "last_closed": _serialize(last_closed) if last_closed else None,
        "history": [_serialize(cr) for cr in history],
        "system_totals": system_totals,
        "system_totals_named": system_totals_named,
        "payment_methods": _payment_methods_map(),
    }


@bp.route("/caixa")
@api_login_required
def caixa_status():
    """Retorna o status atual do caixa."""
    return api_response(_caixa_payload())


@bp.route("/caixa/open", methods=["POST"])
@api_login_required
def caixa_open():
    """Abre um novo caixa com o valor informado."""
    repository = CashRegisterRepository()
    if repository.get_open():
        return api_error(
            "Já existe um caixa aberto. Feche-o antes de abrir outro.", 400
        )

    data = request.get_json(silent=True) or {}

    # opening_details: {"1": 100.00, "2": 50.00} (method_id -> amount)
    opening_details_raw = data.get("opening_details")
    if opening_details_raw is None:
        # fallback: aceita opening_amount simples pra compatibilidade
        opening_amount = data.get("opening_amount")
        if opening_amount is None:
            return api_error("Informe o valor de abertura.", 400)
        try:
            opening_amount = round(float(opening_amount), 2)
        except (TypeError, ValueError):
            return api_error("Valor de abertura inválido.", 400)
        if opening_amount < 0:
            return api_error("Valor de abertura não pode ser negativo.", 400)
        opening_details = None
    else:
        if not isinstance(opening_details_raw, dict):
            return api_error("opening_details deve ser um objeto.", 400)
        opening_details = {}
        opening_amount = 0.0
        for mid, val in opening_details_raw.items():
            try:
                v = round(float(val), 2)
            except (TypeError, ValueError):
                return api_error(
                    f"Valor inválido para a forma {mid}.", 400
                )
            if v < 0:
                return api_error(
                    f"Valor da forma {mid} não pode ser negativo.", 400
                )
            opening_details[str(mid)] = v
            opening_amount += v
        opening_amount = round(opening_amount, 2)
        opening_details = json.dumps(opening_details)

    now = datetime.now()
    user = session.get("user", "operador")
    repository.open_register(
        opened_by=user,
        opened_at=now.strftime("%Y-%m-%d %H:%M:%S"),
        opening_amount=opening_amount,
        opening_details=opening_details,
    )
    return api_response(_caixa_payload(), status=201)


@bp.route("/caixa/close", methods=["POST"])
@api_login_required
def caixa_close():
    """Fecha o caixa aberto com os valores contados por forma de pagamento."""
    repository = CashRegisterRepository()
    open_register = repository.get_open()
    if not open_register:
        return api_error("Nenhum caixa aberto para fechar.", 400)

    data = request.get_json(silent=True) or {}

    # calcula totais do sistema
    now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    system_totals = repository.compute_system_totals(
        open_register.opened_at, now_str
    )

    # closing_details: {"1": 150.00, "2": 75.00} (method_id -> counted amount)
    closing_details_raw = data.get("closing_details")
    if closing_details_raw is None:
        # fallback: aceita closing_amount simples
        closing_amount = data.get("closing_amount")
        if closing_amount is None:
            return api_error("Informe o valor contado no fechamento.", 400)
        try:
            closing_amount = round(float(closing_amount), 2)
        except (TypeError, ValueError):
            return api_error("Valor de fechamento inválido.", 400)
        if closing_amount < 0:
            return api_error("Valor de fechamento não pode ser negativo.", 400)
        closing_details = None
    else:
        if not isinstance(closing_details_raw, dict):
            return api_error("closing_details deve ser um objeto.", 400)
        closing_details = {}
        closing_amount = 0.0
        for mid, val in closing_details_raw.items():
            try:
                v = round(float(val), 2)
            except (TypeError, ValueError):
                return api_error(
                    f"Valor inválido para a forma {mid}.", 400
                )
            if v < 0:
                return api_error(
                    f"Valor da forma {mid} não pode ser negativo.", 400
                )
            closing_details[str(mid)] = v
            closing_amount += v
        closing_amount = round(closing_amount, 2)
        closing_details = json.dumps(closing_details)

    # soma dos opening_details
    expected_amount = open_register.opening_amount + sum(system_totals.values())
    expected_amount = round(expected_amount, 2)

    now = datetime.now()
    user = session.get("user", "operador")

    repository.close_register(
        register_id=open_register.id,
        closed_by=user,
        closed_at=now.strftime("%Y-%m-%d %H:%M:%S"),
        closing_amount=closing_amount,
        expected_amount=expected_amount,
        obs=(data.get("obs") or "").strip() or None,
        system_totals=json.dumps(system_totals),
        closing_details=closing_details,
    )
    return api_response(_caixa_payload())
