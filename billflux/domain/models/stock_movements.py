"""Module for named tuple, stock movement report model"""

from collections import namedtuple

StockMovement = namedtuple(
    "StockMovement",
    [
        "id",
        "product_id",
        "product_name",
        "movement_type",
        "quantity",
        "obs",
        "created_at",
    ],
)
