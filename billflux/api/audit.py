"""Endpoint de leitura da trilha de auditoria da API JSON."""

from flask import request

from billflux.api import bp, api_login_required, api_response
from billflux.infra.repository.audit_repository import AuditRepository


@bp.route("/audit")
@api_login_required
def audit_list():
    """Últimos eventos de auditoria, com filtros opcionais."""
    args = request.args
    try:
        limit = max(1, min(int(args.get("limit", 50)), 200))
    except (TypeError, ValueError):
        limit = 50
    events = AuditRepository().list_recent(
        limit=limit,
        entity=args.get("entity") or None,
        action=args.get("action") or None,
    )
    return api_response(
        {
            "events": [
                {
                    "id": e.id,
                    "actor": e.actor,
                    "action": e.action,
                    "entity": e.entity,
                    "entity_id": e.entity_id,
                    "details": e.details,
                    "created_at": (
                        e.created_at.isoformat()
                        if hasattr(e.created_at, "isoformat")
                        else e.created_at
                    ),
                }
                for e in events
            ]
        }
    )
