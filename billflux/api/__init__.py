"""API JSON do BillFlux (usada pelo frontend SPA)."""

import json
from datetime import date, datetime
from decimal import Decimal, InvalidOperation
from functools import wraps

from flask import Response, session
from flask.blueprints import Blueprint

bp = Blueprint("bp_api", __name__, url_prefix="/api")


def br_to_decimal(value):
    """Converte número ou string BR ('1.234,56') para Decimal ou None."""
    if value is None or value == "":
        return None
    if isinstance(value, (int, float)):
        return Decimal(str(value))
    raw = str(value).strip()
    try:
        if "," in raw:
            return Decimal(raw.replace(".", "").replace(",", "."))
        return Decimal(raw)
    except InvalidOperation:
        return None


def _json_default(obj):
    """Serializa Decimal como string e datas como ISO."""
    if isinstance(obj, Decimal):
        return str(obj)
    if isinstance(obj, (datetime, date)):
        return obj.isoformat()
    raise TypeError(f"Tipo não serializável: {type(obj)}")


def api_response(data, status=200):
    """Resposta JSON com encoding de Decimal/date por padrão."""
    return Response(
        json.dumps(data, ensure_ascii=False, default=_json_default),
        status=status,
        mimetype="application/json",
    )


def api_error(message, status=400):
    """Resposta JSON de erro no padrão {"error": "..."}."""
    return api_response({"error": message}, status=status)


def api_login_required(view):
    """Exige sessão autenticada; devolve 401 JSON caso contrário."""

    @wraps(view)
    def wrapped(*args, **kwargs):
        if not session.get("user"):
            return api_error("Não autenticado.", 401)
        return view(*args, **kwargs)

    return wrapped
