"""Helper de auditoria: registra eventos sem quebrar o fluxo principal."""

from flask import session

from billflux.infra.repository.audit_repository import AuditRepository


def audit(action, entity=None, entity_id=None, details=None):
    """Registra um evento de auditoria (best-effort, nunca levanta erro)."""
    try:
        actor = session.get("user", "sistema")
    except Exception:
        actor = "sistema"
    try:
        AuditRepository().record(
            action=action,
            actor=actor or "sistema",
            entity=entity,
            entity_id=entity_id,
            details=details,
        )
    except Exception:
        pass
