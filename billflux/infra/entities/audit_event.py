"""Module for model AuditEvent (trilha de auditoria)"""

from datetime import datetime
from typing import Optional

from sqlmodel import SQLModel, Field


class AuditEvent(SQLModel, table=True):
    """Evento relevante para auditoria (quem fez o quê, quando)"""

    __tablename__ = "audit_event"

    id: Optional[int] = Field(default=None, primary_key=True)
    actor: str = Field(nullable=False, default="sistema")
    action: str = Field(nullable=False)
    entity: Optional[str] = Field(default=None, nullable=True)
    entity_id: Optional[int] = Field(default=None, nullable=True)
    details: Optional[str] = Field(default=None, nullable=True)
    created_at: datetime = Field(default_factory=datetime.now, nullable=False)
