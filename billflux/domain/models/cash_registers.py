"""Module for named tuple, cash register model"""

from collections import namedtuple

CashRegister = namedtuple(
    "CashRegister",
    [
        "id",
        "opened_by",
        "opened_at",
        "opening_amount",
        "closed_by",
        "closed_at",
        "closing_amount",
        "expected_amount",
        "status",
        "obs",
        "opening_details",
        "system_totals",
        "closing_details",
    ],
)
