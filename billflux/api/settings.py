"""Endpoints de configurações editáveis (tela Configurações) da API JSON."""

from flask import request

from billflux.api import bp, api_error, api_login_required, api_response
from billflux.infra.repository.settings_repository import SettingsRepository
from billflux.services.audit import audit


@bp.route("/settings")
@api_login_required
def settings_get():
    """Devolve todas as configurações editáveis (nunca segredos)."""
    return api_response({"settings": SettingsRepository().get_all()})


@bp.route("/settings", methods=["PUT"])
@api_login_required
def settings_put():
    """Grava configurações (somente chaves permitidas)."""
    data = request.get_json(silent=True) or {}
    values = data.get("settings")
    if not isinstance(values, dict):
        return api_error("Envie um objeto 'settings'.", 400)
    saved = SettingsRepository().set_many(values)
    audit("settings.update", entity="setting", details={"keys": sorted(values.keys())})
    return api_response({"settings": saved})
