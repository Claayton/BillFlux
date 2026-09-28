"""Module for named tuple, cash movement model"""

from collections import namedtuple

CashMovement = namedtuple(
    "CashMovement",
    [
        "id",
        "cash_register_id",
        "kind",
        "amount",
        "obs",
        "created_by",
        "created_at",
    ],
)
