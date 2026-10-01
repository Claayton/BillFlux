"""Module for repository to AuditEvent (trilha de auditoria)"""

import json
from typing import List, Optional

from sqlmodel import select
from billflux.infra.config.database import get_session
from billflux.infra.entities.audit_event import AuditEvent as AuditEventModel
from billflux.domain.models.audit_events import AuditEvent


def _to_domain(e: AuditEventModel) -> AuditEvent:
    return AuditEvent(
        id=e.id,
        actor=e.actor,
        action=e.action,
        entity=e.entity,
        entity_id=e.entity_id,
        details=e.details,
        created_at=e.created_at,
    )


class AuditRepository:
    """AuditEvent table data manipulation (somente escrita + leitura)."""

    def record(
        self,
        action: str,
        actor: str = "sistema",
        entity: str | None = None,
        entity_id: int | None = None,
        details: dict | None = None,
    ) -> AuditEvent:
        """Registra um evento. Nunca deve quebrar o fluxo principal."""
        session = get_session()
        try:
            with session:
                model = AuditEventModel(
                    actor=actor,
                    action=action,
                    entity=entity,
                    entity_id=entity_id,
                    details=(
                        json.dumps(details, ensure_ascii=False) if details else None
                    ),
                )
                session.add(model)
                session.commit()
                session.refresh(model)
                return _to_domain(model)
        finally:
            session.close()

    def list_recent(
        self, limit: int = 50, entity: str | None = None, action: str | None = None
    ) -> List[AuditEvent]:
        """Eventos mais recentes, com filtros opcionais."""
        session = get_session()
        try:
            with session:
                stmt = (
                    select(AuditEventModel)
                    .order_by(AuditEventModel.id.desc())
                    .limit(limit)
                )
                if entity:
                    stmt = stmt.where(AuditEventModel.entity == entity)
                if action:
                    stmt = stmt.where(AuditEventModel.action == action)
                return [_to_domain(e) for e in session.exec(stmt).all()]
        finally:
            session.close()
