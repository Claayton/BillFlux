"""Module for named tuple, audit event model"""

from collections import namedtuple

AuditEvent = namedtuple(
    "AuditEvent",
    [
        "id",
        "actor",
        "action",
        "entity",
        "entity_id",
        "details",
        "created_at",
    ],
)
