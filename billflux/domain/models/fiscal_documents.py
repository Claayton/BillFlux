"""Module for named tuple, fiscal document model"""

from collections import namedtuple

FiscalDocument = namedtuple(
    "FiscalDocument",
    [
        "id",
        "order_id",
        "provider",
        "model",
        "environment",
        "status",
        "series",
        "number",
        "access_key",
        "protocol",
        "xml",
        "danfe",
        "qr_code_url",
        "error_code",
        "error_message",
        "retry_count",
        "next_retry_at",
        "created_at",
        "updated_at",
        "authorized_at",
        "cancelled_at",
        "cancel_reason",
    ],
)
